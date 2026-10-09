"""Datos de demostración realistas para evaluar Inventia sin cargar información real.

Crea una empresa ficticia de movilidad eléctrica (bicicletas, monopatines y motos eléctricas, baterías,
repuestos y accesorios) con tres sedes, seis categorías, 36 productos y un historial de ventas y
compras con estacionalidad semanal, tendencia, ruido, rupturas de stock, un producto nuevo, uno sin
rotación y un excedente en una sede. TODO pasa por los mismos servicios que usa la API (reglas de
negocio, movimientos inmutables, auditoría), nunca por inserciones directas.

Las contraseñas se generan al azar en cada carga y se muestran UNA vez; no hay credenciales fijas.

Dos modos:
- Por defecto crea también la empresa y su administrador (con contraseña aleatoria).
- ``en_empresa_existente=True`` carga los datos en la empresa que ya creó la persona con la pantalla de
  configuración inicial: su administrador conserva su correo y su contraseña, y solo se generan las
  credenciales de los demás usuarios de ejemplo.
"""

import math
import secrets
import string
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contexto_de_usuario
from app.core.exceptions import Conflicto
from app.core.security import hash_password
from app.core.tiempo import ZONA, hoy_local
from app.models.acceso import Rol
from app.models.catalogo import Categoria, Producto
from app.models.empresa import Empresa
from app.models.enums import TipoMovimiento
from app.models.inventario import InventarioSede
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.ventas import VentaCrear, VentaItemCrear
from app.services import alertas_service, inventario_service, setup_service, ventas_service
from app.services.inventario_service import Operacion

DOMINIO = "demo.inventia.example"

# Perfil semanal (lunes … domingo) por tipo de producto.
_PERFILES = {
    "vehiculo": [0.7, 0.7, 0.8, 0.9, 1.2, 1.9, 1.1],  # se compran sobre todo el fin de semana
    "repuesto": [1.3, 1.2, 1.1, 1.1, 1.1, 0.8, 0.4],  # lo piden los talleres entre semana
    "accesorio": [0.8, 0.8, 0.9, 1.0, 1.3, 1.5, 1.0],
    "energia": [1.1, 1.0, 1.0, 1.0, 1.1, 1.0, 0.8],
}

# (código, nombre, categoría, unidad, costo, precio, demanda diaria base en la sede de referencia, perfil)
# Precios en pesos colombianos. Los vehículos se venden pocos por día (demanda intermitente); los repuestos y
# accesorios rotan mucho más.
CATALOGO: list[tuple[str, str, str, str, int, int, float, str]] = [
    ("BIC-001", "Bicicleta eléctrica urbana 250 W 36 V", "Bicicletas eléctricas", "unidad", 2300000, 3190000, 1.2, "vehiculo"),
    ("BIC-002", "Bicicleta eléctrica de montaña 500 W 48 V", "Bicicletas eléctricas", "unidad", 3600000, 4890000, 0.4, "vehiculo"),
    ("BIC-003", "Bicicleta eléctrica plegable 250 W", "Bicicletas eléctricas", "unidad", 2100000, 2950000, 0.7, "vehiculo"),
    ("BIC-004", "Bicicleta eléctrica de carga 750 W", "Bicicletas eléctricas", "unidad", 5200000, 6990000, 0.15, "vehiculo"),
    ("BIC-005", "Kit de conversión a bicicleta eléctrica 500 W", "Bicicletas eléctricas", "unidad", 1250000, 1790000, 0.3, "vehiculo"),
    ("MON-001", "Monopatín eléctrico 350 W, 25 km de autonomía", "Monopatines eléctricos", "unidad", 1150000, 1690000, 1.6, "vehiculo"),
    ("MON-002", "Monopatín eléctrico 500 W, 40 km de autonomía", "Monopatines eléctricos", "unidad", 1900000, 2690000, 1.0, "vehiculo"),
    ("MON-003", "Monopatín eléctrico todoterreno 800 W", "Monopatines eléctricos", "unidad", 3100000, 4190000, 0.2, "vehiculo"),
    ("MON-004", "Monopatín eléctrico plegable ultraligero", "Monopatines eléctricos", "unidad", 1400000, 1990000, 0.45, "vehiculo"),
    ("MON-005", "Monopatín eléctrico infantil 120 W", "Monopatines eléctricos", "unidad", 650000, 990000, 0.5, "vehiculo"),
    ("MOT-001", "Moto eléctrica urbana 3000 W", "Motos eléctricas", "unidad", 6800000, 8990000, 0.25, "vehiculo"),
    ("MOT-002", "Moto eléctrica de reparto 4000 W", "Motos eléctricas", "unidad", 8400000, 10900000, 0.18, "vehiculo"),
    ("MOT-003", "Scooter eléctrico 2000 W", "Motos eléctricas", "unidad", 5200000, 6990000, 0.28, "vehiculo"),
    ("MOT-004", "Moto eléctrica deportiva 5000 W", "Motos eléctricas", "unidad", 12500000, 16500000, 0.08, "vehiculo"),
    ("BAT-001", "Batería de litio 36 V 10 Ah", "Baterías y cargadores", "unidad", 520000, 790000, 1.4, "energia"),
    ("BAT-002", "Batería de litio 48 V 15 Ah", "Baterías y cargadores", "unidad", 890000, 1290000, 1.1, "energia"),
    ("BAT-003", "Batería de litio 60 V 20 Ah para moto", "Baterías y cargadores", "unidad", 1650000, 2390000, 0.4, "energia"),
    ("BAT-004", "Cargador inteligente 36 V 2 A", "Baterías y cargadores", "unidad", 95000, 165000, 2.4, "energia"),
    ("BAT-005", "Cargador rápido 48 V 5 A", "Baterías y cargadores", "unidad", 210000, 330000, 1.2, "energia"),
    ("BAT-006", "Cargador portátil para monopatín 42 V", "Baterías y cargadores", "unidad", 85000, 149000, 1.6, "energia"),
    ("REP-001", "Motor de buje 250 W 36 V", "Repuestos y componentes", "unidad", 280000, 450000, 1.0, "repuesto"),
    ("REP-002", "Controlador 36/48 V 15 A", "Repuestos y componentes", "unidad", 120000, 210000, 1.3, "repuesto"),
    ("REP-003", "Pantalla LCD para bicicleta eléctrica", "Repuestos y componentes", "unidad", 85000, 155000, 1.2, "repuesto"),
    ("REP-004", "Acelerador de puño", "Repuestos y componentes", "unidad", 22000, 49000, 3.0, "repuesto"),
    ("REP-005", "Sensor de pedaleo (PAS)", "Repuestos y componentes", "unidad", 28000, 59000, 2.0, "repuesto"),
    ("REP-006", "Llanta 10 pulgadas para monopatín", "Repuestos y componentes", "unidad", 38000, 79000, 3.2, "repuesto"),
    ("REP-007", "Cámara de repuesto 10 pulgadas", "Repuestos y componentes", "unidad", 12000, 29000, 6.0, "repuesto"),
    ("REP-008", "Pastillas de freno de disco", "Repuestos y componentes", "par", 14000, 35000, 7.0, "repuesto"),
    ("REP-009", "Cable de freno con sensor de corte", "Repuestos y componentes", "unidad", 16000, 39000, 0.15, "repuesto"),
    ("REP-010", "Guardabarros delantero y trasero", "Repuestos y componentes", "paquete", 25000, 55000, 1.5, "repuesto"),
    ("ACC-001", "Casco con luz trasera", "Accesorios y seguridad", "unidad", 78000, 139000, 3.0, "accesorio"),
    ("ACC-002", "Candado de cadena antirrobo", "Accesorios y seguridad", "unidad", 42000, 89000, 2.6, "accesorio"),
    ("ACC-003", "Luz delantera LED recargable", "Accesorios y seguridad", "unidad", 18000, 45000, 5.5, "accesorio"),
    ("ACC-004", "Soporte de celular con carga USB", "Accesorios y seguridad", "unidad", 24000, 59000, 3.4, "accesorio"),
    ("ACC-005", "Bolso de manubrio impermeable", "Accesorios y seguridad", "unidad", 55000, 105000, 1.6, "accesorio"),
    ("ACC-006", "Rodilleras y coderas (juego)", "Accesorios y seguridad", "paquete", 48000, 95000, 1.3, "accesorio"),
]
CATEGORIAS = [
    "Bicicletas eléctricas", "Monopatines eléctricos", "Motos eléctricas", "Baterías y cargadores",
    "Repuestos y componentes", "Accesorios y seguridad",
]

# (nombre, ciudad, dirección, factor de volumen)
SEDES = [
    ("Sede Principal", "Medellín", "Carrera 43A # 14-50", 1.4),
    ("Sede Norte", "Medellín", "Carrera 64C # 78-30", 1.0),
    ("Sede Sur", "Envigado", "Calle 37 Sur # 43A-20", 0.7),
]

NUEVO = "MON-004"  # modelo lanzado hace pocos días: historial insuficiente a propósito
SIN_ROTACION = ("REP-003", "Sede Sur")  # pantallas de un modelo descontinuado: existencias que nunca se venden
EXCEDENTE = ("REP-007", "Sede Sur")  # compra desproporcionada de cámaras: excedente que puede trasladarse
INTERMITENTE = "REP-009"  # se vende muy de vez en cuando
PROPENSO_A_RUPTURA = {"REP-008", "ACC-003", "BAT-004", "REP-007"}  # reposición corta: generan días sin existencias


@dataclass
class ResultadoDemo:
    empresa_id: int
    credenciales: list[tuple[str, str, str]] = field(default_factory=list)  # (rol, correo, contraseña)
    ventas: int = 0
    movimientos_entrada: int = 0
    desde: date | None = None
    hasta: date | None = None


def _clave_aleatoria() -> str:
    base = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    return f"{base}#9aA"  # cumple la política: mayúscula, minúscula, número y símbolo


def _momento(dia: date, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(dia, time(hora, minuto), tzinfo=ZONA).astimezone(timezone.utc)


class SinAlertas:
    """Durante la carga masiva las alertas se calculan UNA vez al final, no en cada venta."""

    def __enter__(self):
        self._original = alertas_service.sincronizar

        async def _nada(db, empresa_id, pares):
            return {"abiertas": 0, "resueltas": 0, "actualizadas": 0}

        alertas_service.sincronizar = _nada
        return self

    def __exit__(self, *exc):
        alertas_service.sincronizar = self._original


async def _empresa_existente_vacia(db: AsyncSession) -> tuple[Empresa, Usuario]:
    """La única empresa de la base (la de la configuración inicial), que debe estar vacía, y su administrador."""
    empresas = (await db.scalars(select(Empresa))).all()
    if len(empresas) != 1:
        raise Conflicto(
            "Para cargar la demostración en una empresa existente la base debe tener exactamente una empresa "
            f"(tiene {len(empresas)}).",
            codigo="demo_empresa_no_unica",
        )
    empresa = empresas[0]
    for modelo in (Sede, Producto):
        if await db.scalar(select(func.count()).select_from(modelo).where(modelo.empresa_id == empresa.id)):
            raise Conflicto(
                "La empresa ya tiene sedes o productos. La demostración solo se carga en una empresa recién creada.",
                codigo="demo_empresa_con_datos",
            )
    admin = await db.scalar(
        select(Usuario).join(Rol, Usuario.rol_id == Rol.id)
        .where(Usuario.empresa_id == empresa.id, Rol.clave == "admin", Usuario.activo.is_(True))
        .order_by(Usuario.id).limit(1)
    )
    if admin is None:
        raise Conflicto("La empresa no tiene un administrador activo.", codigo="demo_sin_administrador")
    return empresa, admin


async def cargar_demo(
    db: AsyncSession,
    *,
    dias: int = 120,
    semilla: int = 7,
    productos: int | None = None,
    sufijo: str = "",
    en_empresa_existente: bool = False,
    avance: Callable[[str], None] | None = None,
) -> ResultadoDemo:
    """Carga la demostración con ``dias`` de historial que terminan ayer (ver el modo en la cabecera del módulo)."""
    informar = avance or (lambda _m: None)
    rng = np.random.default_rng(semilla)
    hoy = hoy_local()
    inicio = hoy - timedelta(days=dias)
    catalogo = CATALOGO[:productos] if productos else CATALOGO

    if en_empresa_existente:
        empresa, admin = await _empresa_existente_vacia(db)
        resultado = ResultadoDemo(empresa_id=empresa.id, desde=inicio, hasta=hoy - timedelta(days=1))
    else:
        clave_admin = _clave_aleatoria()
        empresa, admin = await setup_service.crear_empresa_con_admin(
            db, nombre=f"Movilidad Eléctrica Andina (demostración){sufijo}", identificacion=None,
            direccion="Carrera 43A # 14-50", ciudad="Medellín", telefono=None, email_empresa=f"contacto{sufijo}@{DOMINIO}",
            admin_nombre="Administración Demo", admin_email=f"admin{sufijo}@{DOMINIO}", admin_password=clave_admin,
        )
        resultado = ResultadoDemo(empresa_id=empresa.id, desde=inicio, hasta=hoy - timedelta(days=1))
        resultado.credenciales.append(("Administrador", admin.email, clave_admin))

    roles = {r.clave: r for r in (await db.scalars(select(Rol).where(Rol.empresa_id == empresa.id))).all()}
    sedes: dict[str, Sede] = {}
    for nombre, ciudad, direccion, _f in SEDES:
        sede = Sede(empresa_id=empresa.id, nombre=nombre, ciudad=ciudad, direccion=direccion)
        db.add(sede)
        sedes[nombre] = sede
    await db.flush()

    def _usuario(rol: str, nombre: str, correo: str, sede: Sede | None) -> Usuario:
        clave = _clave_aleatoria()
        u = Usuario(
            empresa_id=empresa.id, rol_id=roles[rol].id, sede_id=sede.id if sede else None, nombre=nombre,
            email=f"{correo}{sufijo}@{DOMINIO}", password_hash=hash_password(clave),
        )
        db.add(u)
        resultado.credenciales.append((roles[rol].nombre, u.email, clave))
        return u

    _usuario("gerente", "Gerencia Demo", "gerente", None)
    analista = _usuario("analista_compras", "Compras Demo", "compras", None)
    encargados = {n: _usuario("encargado_sede", f"Encargado {n}", f"encargado.{i + 1}", s) for i, (n, s) in enumerate(sedes.items())}
    _usuario("usuario_inventario", "Inventario Demo", "inventario", sedes["Sede Principal"])
    await db.flush()
    await db.commit()

    categorias = {}
    for nombre in CATEGORIAS:
        c = Categoria(empresa_id=empresa.id, nombre=nombre)
        db.add(c)
        categorias[nombre] = c
    await db.flush()
    objetos: dict[str, Producto] = {}
    for codigo, nombre, cat, unidad, costo, precio, _b, _p in catalogo:
        p = Producto(
            empresa_id=empresa.id, categoria_id=categorias[cat].id, codigo=codigo, nombre=nombre, unidad_medida=unidad,
            costo=costo, precio_venta=precio,
        )
        db.add(p)
        objetos[codigo] = p
    await db.flush()
    await db.commit()

    ctx_admin = contexto_de_usuario(await db.scalar(select(Usuario).where(Usuario.id == admin.id).execution_options(populate_existing=True)))
    ctx_sede = {
        n: contexto_de_usuario(await db.scalar(select(Usuario).where(Usuario.id == u.id).execution_options(populate_existing=True)))
        for n, u in encargados.items()
    }

    # --- estado de la simulación por (sede, producto) ---
    estado: dict[tuple[str, str], dict] = {}
    for sede_nombre, _c, _d, factor in SEDES:
        for codigo, _n, _cat, _u, _co, _pr, base, perfil in catalogo:
            if (codigo, sede_nombre) == SIN_ROTACION:
                demanda = 0.0
            elif codigo == INTERMITENTE:
                demanda = base  # intermitente (0,15 / día)
            else:
                demanda = base * factor * float(np.exp(rng.normal(0, 0.15)))
            ya_vende = (inicio + timedelta(days=dias - 12)) if codigo == NUEVO else inicio
            estado[(sede_nombre, codigo)] = {
                "demanda": demanda, "perfil": _PERFILES[perfil], "stock": 0, "pendiente": [], "desde": ya_vende,
                "vendido": [], "tendencia": float(rng.choice([-0.001, 0.0, 0.0, 0.001, 0.002])),
            }

    informar(f"Simulando {dias} días de operación en {len(SEDES)} sedes…")
    with SinAlertas():
        for k in range(dias):
            dia = inicio + timedelta(days=k)
            for sede_nombre, _c, _d, _f in SEDES:
                sede = sedes[sede_nombre]
                ops: list[Operacion] = []
                for codigo, st in ((c, s) for (sn, c), s in estado.items() if sn == sede_nombre):
                    if dia < st["desde"]:
                        continue
                    producto = objetos[codigo]
                    if dia == st["desde"]:  # primera compra: inventario inicial
                        cantidad = max(int(math.ceil(max(st["demanda"], 0.3) * 30)), 6)
                        if (codigo, sede_nombre) == EXCEDENTE:
                            cantidad = int(math.ceil(st["demanda"] * dias)) + 160  # lo que se vende en el periodo y 160 de sobra
                        if (codigo, sede_nombre) == SIN_ROTACION:
                            cantidad = 35
                        ops.append(Operacion(sede.id, producto, cantidad, TipoMovimiento.ENTRADA, "inventario_inicial", None))
                        st["stock"] += cantidad
                    llegadas = [q for d, q in st["pendiente"] if d <= dia]
                    if llegadas:
                        st["pendiente"] = [(d, q) for d, q in st["pendiente"] if d > dia]
                        ops.append(Operacion(sede.id, producto, sum(llegadas), TipoMovimiento.ENTRADA, "compra", None))
                        st["stock"] += sum(llegadas)
                if ops:
                    await inventario_service.aplicar_lote(
                        db, empresa_id=empresa.id, usuario_id=admin.id, operaciones=ops, fecha=_momento(dia, 7, 30)
                    )
                    resultado.movimientos_entrada += len(ops)

                # --- ventas del día ---
                lineas: list[tuple[str, int]] = []
                for codigo, st in ((c, s) for (sn, c), s in estado.items() if sn == sede_nombre):
                    if dia < st["desde"] or st["demanda"] <= 0 or st["stock"] <= 0:
                        continue
                    lam = st["demanda"] * st["perfil"][dia.weekday()] * (1 + st["tendencia"] * k)
                    unidades = min(int(rng.poisson(max(lam, 0.0))), st["stock"])
                    st["vendido"].append(unidades)
                    if unidades > 0:
                        lineas.append((codigo, unidades))
                        st["stock"] -= unidades
                rng.shuffle(lineas)
                i = 0
                while i < len(lineas):
                    n = int(rng.integers(1, 5))
                    tiquete = lineas[i : i + n]
                    i += n
                    venta = VentaCrear(
                        sede_id=sede.id, observacion=None,
                        items=[VentaItemCrear(producto_id=objetos[c].id, cantidad=u) for c, u in tiquete],
                    )
                    await ventas_service.registrar_venta(
                        db, ctx_sede[sede_nombre], venta,
                        fecha=_momento(dia, int(rng.integers(9, 20)), int(rng.integers(0, 60))), confirmar=False,
                    )
                    resultado.ventas += 1
                await db.commit()

                # --- revisión diaria de compras: reposición con plazo de entrega de 6 días ---
                if True:
                    for (sn, codigo), st in estado.items():
                        if sn != sede_nombre or st["demanda"] <= 0 or dia < st["desde"]:
                            continue
                        en_camino = sum(q for _d, q in st["pendiente"])
                        reciente = st["vendido"][-21:]
                        consumo = float(np.mean(reciente)) if len(reciente) >= 7 else st["demanda"]  # lo que compras se ajusta a lo que vendes
                        cobertura_objetivo = 8 if codigo in PROPENSO_A_RUPTURA else 30
                        umbral = 3 if codigo in PROPENSO_A_RUPTURA else 16
                        if (codigo, sede_nombre) == EXCEDENTE:
                            continue
                        if st["stock"] + en_camino < consumo * umbral:
                            pedir = int(math.ceil(consumo * cobertura_objetivo - st["stock"] - en_camino))
                            if pedir > 0:
                                st["pendiente"].append((dia + timedelta(days=6), pedir))
            if (k + 1) % 20 == 0:
                informar(f"  {k + 1}/{dias} días simulados · {resultado.ventas} ventas")

    # Niveles mínimo y máximo coherentes con el consumo de cada sede.
    filas = (await db.scalars(select(InventarioSede).where(InventarioSede.empresa_id == empresa.id))).all()
    codigo_de = {p.id: c for c, p in objetos.items()}
    nombre_de = {s.id: n for n, s in sedes.items()}
    for fila in filas:
        st = estado[(nombre_de[fila.sede_id], codigo_de[fila.producto_id])]
        minimo = int(math.ceil(st["demanda"] * 5))
        maximo = int(math.ceil(max(st["demanda"], 0.3) * 45))
        if (codigo_de[fila.producto_id], nombre_de[fila.sede_id]) == EXCEDENTE:
            maximo = 60
        if (codigo_de[fila.producto_id], nombre_de[fila.sede_id]) == SIN_ROTACION:
            minimo, maximo = 0, 60
        await db.execute(
            update(InventarioSede).where(InventarioSede.id == fila.id).values(
                stock_minimo=minimo, stock_maximo=max(maximo, minimo),
                created_at=_momento(inicio, 7),  # las existencias existen desde el primer día simulado (alerta de «sin rotación»)
            )
        )
    await db.commit()
    informar("Calculando alertas de inventario…")
    await alertas_service.recalcular_empresa(db, ctx_admin)
    return resultado


async def preparar_prediccion(db: AsyncSession, resultado: ResultadoDemo, avance: Callable[[str], None] | None = None) -> dict:
    """Ejecuta una predicción y genera recomendaciones con los datos de demostración (opcional)."""
    from app.services import prediccion_service, recomendaciones_service

    informar = avance or (lambda _m: None)
    analista = await db.scalar(
        select(Usuario).where(Usuario.empresa_id == resultado.empresa_id, Usuario.email.like(f"compras%@{DOMINIO}"))
        .execution_options(populate_existing=True)
    )
    ctx = contexto_de_usuario(analista)
    informar("Entrenando y validando modelos de pronóstico…")
    try:
        ejecucion = await prediccion_service.solicitar(db, ctx, None)
    except Conflicto:
        raise
    await prediccion_service.ejecutar_en_segundo_plano(ejecucion.id)
    await db.refresh(ejecucion)
    informar("Generando recomendaciones…")
    rec = await recomendaciones_service.generar(db, ctx)
    return {"ejecucion_id": ejecucion.id, "estado": ejecucion.estado, "resumen": ejecucion.resumen, "recomendaciones": rec}
