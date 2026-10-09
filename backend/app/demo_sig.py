"""Datos de demostración del módulo SIG (PQRS, SST, Calidad y Gestión ambiental).

Se cargan DESPUÉS de la demostración general (``cargar-demo``) o sobre cualquier empresa que ya tenga sedes,
productos y usuarios. Todo pasa por los mismos servicios que usa la API (permisos, historial, auditoría), con
una única excepción documentada: el historial de pausas activas se inserta directamente, porque el servicio
solo registra pausas en tiempo real y respeta el intervalo configurado.

Gestión ambiental: se dejan configurados el factor de la red y los parámetros de las categorías de vehículos con
VALORES DE DEMOSTRACIÓN, rotulados como tales en el campo «fuente». No provienen de una ficha técnica ni de un
estudio: antes de usar las cifras en un informe real hay que reemplazarlos por datos documentados.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contexto_de_usuario
from app.core.acceso import Contexto
from app.core.exceptions import Conflicto
from app.core.tiempo import hoy_local
from app.demo import _momento
from app.models.acceso import Rol
from app.models.catalogo import Categoria, Producto
from app.models.empresa import Empresa
from app.models.pqrs import Pqrs
from app.models.sst import SstPausa
from app.models.usuario import Usuario
from app.schemas.ambiental import CategoriaAmbientalActualizar, FactorRedActualizar
from app.schemas.calidad import GarantiaCrear, GarantiaGestionar, NoConformidadCrear, NoConformidadGestionar, ObservacionCrear
from app.schemas.inventario import EntradaCrear, EntradaObservacionCrear, ItemCantidad
from app.schemas.pqrs import PqrsCrear, PqrsGestionar
from app.services import ambiental_service, calidad_service, entradas_service, inventario_service, pqrs_service, sst_service

FUENTE_DEMO = (
    "VALORES DE DEMOSTRACIÓN: no provienen de una ficha técnica ni de un estudio. "
    "Reemplácelos por datos documentados antes de usar las cifras en un informe."
)
FUENTE_FACTOR_DEMO = (
    "VALOR DE DEMOSTRACIÓN basado en la referencia pública de la UPME para 2024 (0,220 kg CO₂eq/kWh). "
    "Verifique la cifra vigente en www.upme.gov.co."
)
REFERENCIA_MOTO = "Motocicleta de combustión de baja cilindrada (referencia de demostración)"

# categoría → (tipo, propulsión, km/año, kWh/100 km, vehículo de referencia, g CO₂/km)
PARAMETROS_DEMO: dict[str, tuple[str, str, str, str, str, str]] = {
    "Bicicletas eléctricas": ("bicicleta_electrica", "asistida_pedaleo", "1500", "1.0", REFERENCIA_MOTO, "80"),
    "Monopatines eléctricos": ("patineta_electrica", "electrica", "1000", "1.5", REFERENCIA_MOTO, "80"),
    "Motos eléctricas": ("motocicleta_electrica", "electrica", "5000", "4.0", "Motocicleta de combustión de 150 cc (referencia de demostración)", "100"),
}


@dataclass
class ResultadoDemoSig:
    pqrs: int = 0
    entradas: int = 0
    no_conformidades: int = 0
    garantias: int = 0
    pausas: int = 0
    ambiental_configurado: bool = False
    vehiculos_incorporados: int = 0


async def _contexto(db: AsyncSession, usuario: Usuario) -> Contexto:
    recargado = await db.scalar(select(Usuario).where(Usuario.id == usuario.id).execution_options(populate_existing=True))
    return contexto_de_usuario(recargado)


async def _usuarios(db: AsyncSession, empresa_id: int, *claves: str) -> list[Usuario]:
    return list(
        (await db.scalars(
            select(Usuario).join(Rol, Usuario.rol_id == Rol.id)
            .where(Usuario.empresa_id == empresa_id, Rol.clave.in_(claves), Usuario.activo.is_(True)).order_by(Usuario.id)
        )).all()
    )


async def _productos(db: AsyncSession, empresa_id: int, codigos: list[str]) -> list[Producto]:
    """Los productos pedidos por código; si no existen (empresa con otro catálogo) se completa con otros activos."""
    todos = list((await db.scalars(select(Producto).where(Producto.empresa_id == empresa_id, Producto.activo.is_(True)).order_by(Producto.id))).all())
    por_codigo = {p.codigo: p for p in todos}
    elegidos: list[Producto] = []
    for codigo in codigos:
        producto = por_codigo.get(codigo) or next((p for p in todos if p not in elegidos), None)
        if producto is None:
            raise Conflicto("La empresa no tiene productos activos para la demostración.", codigo="demo_sig_sin_productos")
        elegidos.append(producto)
    return elegidos


# --------------------------------------------------------------------------- PQRS


async def _pqrs(db: AsyncSession, autores: list[Contexto], admin: Contexto, resultado: ResultadoDemoSig) -> None:
    a, b, c = autores[0], autores[1 % len(autores)], autores[-1]
    casos = [
        (a, "peticion", "Capacitación en lectura de códigos de barras", "Solicito una breve capacitación para el equipo de la sede sobre el uso del lector de códigos de barras en las entradas.", "en_revision", None),
        (b, "queja", "Demoras en la aprobación de traslados entre sedes", "Los traslados solicitados por la tarde se aprueban hasta el día siguiente y se agota el stock de accesorios en la sede.", "en_proceso", "Se acordó revisar las solicitudes de traslado dos veces al día (10:00 y 16:00). Haremos seguimiento durante dos semanas."),
        (a, "reclamo", "Diferencia en el conteo de baterías", "El conteo físico de baterías de 36 V no coincide con el sistema: faltan 2 unidades respecto a lo registrado.", "resuelta", "Se verificó el conteo físico, se encontraron 2 unidades en otra estantería y se dejó la observación en el movimiento. Gracias por avisar."),
        (c, "sugerencia", "Acceso rápido a los productos más vendidos", "Sería útil tener en la pantalla de nueva venta un acceso rápido a los productos de mayor rotación.", None, None),
        (b, "sugerencia", "Pausas activas más temprano en la jornada", "Propongo que la primera pausa activa sea a media mañana y no después del almuerzo.", "resuelta", "Se ajustó el intervalo de las pausas a 45 minutos. Gracias por la sugerencia."),
    ]
    for autor, tipo, asunto, descripcion, estado, respuesta in casos:
        pqrs = await pqrs_service.crear(db, autor, PqrsCrear(tipo=tipo, asunto=asunto, descripcion=descripcion))
        resultado.pqrs += 1
        if estado is None:
            continue
        if estado in ("en_proceso", "resuelta"):
            await pqrs_service.gestionar(db, admin, pqrs.id, PqrsGestionar(estado="en_revision"))
        if estado == "resuelta":
            await pqrs_service.gestionar(db, admin, pqrs.id, PqrsGestionar(estado="en_proceso"))
        await pqrs_service.gestionar(db, admin, pqrs.id, PqrsGestionar(estado=estado, respuesta=respuesta))


# --------------------------------------------------------------------------- Calidad y observaciones de entrada


async def _calidad(db: AsyncSession, operadores: list[Contexto], admin: Contexto, resultado: ResultadoDemoSig) -> None:
    op = operadores[0]
    op2 = operadores[1 % len(operadores)]
    hoy = hoy_local()
    casco, bateria, luz = await _productos(db, admin.empresa_id, ["ACC-001", "BAT-001", "ACC-003"])
    sede1, sede2 = op.sede_id, op2.sede_id

    async def recibir(ctx: Contexto, sede_id: int, lineas: list[tuple[Producto, int]], observacion: str | None) -> int:
        movs, _alertas = await inventario_service.registrar_entrada(
            db, ctx, EntradaCrear(sede_id=sede_id, motivo="compra", observacion=observacion, items=[ItemCantidad(producto_id=p.id, cantidad=q) for p, q in lineas])
        )
        resultado.entradas += 1
        return movs[0].entrada_id

    # Entrada 1: llegó con el empaque golpeado → no conformidad ligada a la observación de la entrada.
    e1 = await recibir(op, sede1, [(casco, 12), (bateria, 6)], "Llegó una caja con el empaque exterior golpeado; se revisa el contenido al desempacar.")
    detalle = await entradas_service.detalle(db, op, await entradas_service.obtener_entrada(db, op, e1))
    obs_inicial = detalle.historial_observaciones[0].id
    await entradas_service.agregar_observacion(
        db, op, e1, EntradaObservacionCrear(contenido="Dos baterías con la carcasa rayada; los cascos llegaron sin novedad.", producto_id=bateria.id)
    )
    nc1 = await calidad_service.crear_nc(db, op, NoConformidadCrear(
        producto_id=bateria.id, tipo="empaque_deteriorado", descripcion="Dos baterías de litio llegaron con la carcasa rayada y el empaque interior roto.",
        fecha_deteccion=hoy - timedelta(days=3), cantidad_afectada=2, proveedor="Proveedor de demostración S. A. S.",
        observaciones="Se separaron las unidades afectadas y se tomaron fotos.", entrada_id=e1, entrada_observacion_id=obs_inicial,
    ))
    resultado.no_conformidades += 1
    await calidad_service.gestionar_nc(db, admin, nc1.id, NoConformidadGestionar(estado="en_revision", comentario="Se contactó al proveedor para reclamar el cambio."))
    await calidad_service.gestionar_nc(db, admin, nc1.id, NoConformidadGestionar(estado="en_proceso_solucion", comentario="El proveedor aceptó reponer las dos unidades."))
    await calidad_service.observar_nc(db, op, nc1.id, ObservacionCrear(contenido="Las unidades afectadas siguen apartadas en bodega a la espera del cambio."))

    # Entrada 2 (otra sede): producto equivocado, ya resuelto.
    e2 = await recibir(op2, sede2, [(luz, 20)], "Pedido recibido completo.")
    nc2 = await calidad_service.crear_nc(db, op2, NoConformidadCrear(
        producto_id=luz.id, tipo="producto_equivocado", descripcion="Entre las luces llegaron 3 unidades de otro modelo, distinto al solicitado en la orden.",
        fecha_deteccion=hoy - timedelta(days=9), cantidad_afectada=3, proveedor="Proveedor de demostración S. A. S.", entrada_id=e2,
    ))
    resultado.no_conformidades += 1
    await calidad_service.gestionar_nc(db, admin, nc2.id, NoConformidadGestionar(estado="en_revision"))
    await calidad_service.gestionar_nc(db, admin, nc2.id, NoConformidadGestionar(estado="en_proceso_solucion", solucion="El proveedor recogió las 3 unidades y envió las correctas."))
    await calidad_service.gestionar_nc(db, admin, nc2.id, NoConformidadGestionar(estado="resuelto"))

    # Una no conformidad recién reportada, sin entrada asociada.
    await calidad_service.crear_nc(db, op, NoConformidadCrear(
        producto_id=casco.id, tipo="defecto_de_fabrica", descripcion="Un casco presenta una fisura en la carcasa cerca de la correa de sujeción.",
        fecha_deteccion=hoy - timedelta(days=1), cantidad_afectada=1, observaciones="Se retiró de la exhibición.",
    ))
    resultado.no_conformidades += 1

    # Garantías en distintos estados.
    g1 = await calidad_service.crear_garantia(db, op, GarantiaCrear(
        producto_id=bateria.id, cantidad=1, documento_tipo="entrada_inventario", entrada_id=e1, fecha_compra=hoy - timedelta(days=3),
        garantia_hasta=hoy + timedelta(days=360), defecto="La batería no mantiene la carga: se descarga en menos de una hora.", proveedor="Proveedor de demostración S. A. S.",
        observaciones="Probada con dos cargadores distintos.",
    ))
    resultado.garantias += 1
    await calidad_service.gestionar_garantia(db, admin, g1.id, GarantiaGestionar(estado="pendiente_revision"))
    await calidad_service.gestionar_garantia(db, admin, g1.id, GarantiaGestionar(estado="enviada_proveedor", comentario="Se envió la unidad con la guía de despacho."))
    await calidad_service.observar_garantia(db, op, g1.id, ObservacionCrear(contenido="El proveedor confirmó la recepción de la unidad."))

    g2 = await calidad_service.crear_garantia(db, op2, GarantiaCrear(
        producto_id=luz.id, cantidad=1, documento_tipo="factura_compra", documento_referencia="FC-2026-0142", fecha_compra=hoy - timedelta(days=40),
        garantia_hasta=hoy + timedelta(days=325), fecha_reporte=hoy - timedelta(days=15), defecto="La luz se apaga sola a los pocos minutos de encenderla.",
        proveedor="Proveedor de demostración S. A. S.",
    ))
    resultado.garantias += 1
    await calidad_service.gestionar_garantia(db, admin, g2.id, GarantiaGestionar(estado="enviada_proveedor"))
    await calidad_service.gestionar_garantia(db, admin, g2.id, GarantiaGestionar(estado="aprobada", respuesta_proveedor="Defecto de fábrica confirmado: se aprueba el cambio."))
    await calidad_service.gestionar_garantia(db, admin, g2.id, GarantiaGestionar(estado="solucionada", solucion="Se entregó una unidad nueva al cliente."))

    g3 = await calidad_service.crear_garantia(db, op, GarantiaCrear(
        producto_id=casco.id, cantidad=1, documento_tipo="otro", documento_referencia="Remisión 884", fecha_compra=hoy - timedelta(days=400),
        garantia_hasta=hoy - timedelta(days=35), fecha_reporte=hoy - timedelta(days=5), defecto="El visor del casco está rayado por el uso diario.",
    ))
    resultado.garantias += 1
    await calidad_service.gestionar_garantia(db, admin, g3.id, GarantiaGestionar(estado="enviada_proveedor", proveedor="Proveedor de demostración S. A. S."))
    await calidad_service.gestionar_garantia(db, admin, g3.id, GarantiaGestionar(estado="rechazada", respuesta_proveedor="El daño corresponde al desgaste por uso y la garantía ya había vencido."))


# --------------------------------------------------------------------------- SST


async def _pausas(db: AsyncSession, admin: Contexto, personas: list[Usuario], resultado: ResultadoDemoSig) -> None:
    """Historial de pausas de los últimos días (solo personas a las que aplican las pausas; administración queda fuera)."""
    await sst_service.asegurar_configuracion(db, admin.empresa_id)
    actividades = await sst_service.listar_actividades(db, admin, incluir_inactivas=False)
    if not actividades:
        return
    azar = random.Random(11)
    hoy = hoy_local()
    for dias_atras in range(10, 0, -1):
        dia = hoy - timedelta(days=dias_atras)
        if dia.weekday() >= 5:
            continue
        for persona in personas:
            for hora, minuto in ((9, 30), (11, 15), (14, 40), (16, 20)):
                momento = _momento(dia, hora, minuto + azar.randint(0, 9))
                actividad = actividades[azar.randrange(len(actividades))]
                realizada = azar.random() < 0.82
                db.add(SstPausa(
                    empresa_id=admin.empresa_id, usuario_id=persona.id, actividad_id=actividad.id, actividad_titulo=actividad.titulo,
                    mostrada_en=momento, estado="realizada" if realizada else "omitida",
                    cerrada_en=momento + timedelta(seconds=azar.randint(50, 95) if realizada else azar.randint(3, 12)),
                    duracion_segundos=min(actividad.duracion_segundos, azar.randint(45, 90)) if realizada else None,
                ))
                resultado.pausas += 1
    await db.commit()


# --------------------------------------------------------------------------- Gestión ambiental


async def _ambiental(db: AsyncSession, admin: Contexto, resultado: ResultadoDemoSig) -> None:
    categorias = {c.nombre: c for c in (await db.scalars(select(Categoria).where(Categoria.empresa_id == admin.empresa_id))).all()}
    objetivo = [n for n in PARAMETROS_DEMO if n in categorias]
    if not objetivo:
        return  # catálogo propio: la administración marca sus categorías desde la pestaña Configuración
    await ambiental_service.guardar_factor_red(db, admin, FactorRedActualizar(valor=Decimal("0.220"), anio=2024, fuente=FUENTE_FACTOR_DEMO))
    for nombre in objetivo:
        tipo, propulsion, km, kwh, referencia, gco2 = PARAMETROS_DEMO[nombre]
        r = await ambiental_service.guardar_categoria(db, admin, categorias[nombre].id, CategoriaAmbientalActualizar(
            tipo_vehiculo=tipo, propulsion=propulsion, distancia_anual_km=Decimal(km), consumo_kwh_100km=Decimal(kwh),
            vehiculo_referencia=referencia, emision_referencia_gco2_km=Decimal(gco2), horizonte_anios=1, fuente=FUENTE_DEMO, activa=True,
        ))
        resultado.vehiculos_incorporados += r.incorporados
    resultado.ambiental_configurado = True


# --------------------------------------------------------------------------- orquestación


async def cargar_demo_sig(
    db: AsyncSession, *, empresa_id: int | None = None, avance: Callable[[str], None] | None = None
) -> ResultadoDemoSig:
    informar = avance or (lambda _m: None)
    if empresa_id is None:
        empresas = (await db.scalars(select(Empresa))).all()
        if len(empresas) != 1:
            raise Conflicto(f"Indica la empresa: la base tiene {len(empresas)}.", codigo="demo_sig_empresa_no_unica")
        empresa_id = empresas[0].id
    if await db.scalar(select(func.count()).select_from(Pqrs).where(Pqrs.empresa_id == empresa_id)):
        raise Conflicto(
            "La demostración del SIG ya se cargó (hay solicitudes PQRS registradas). No se cargó de nuevo para no duplicar datos.",
            codigo="demo_sig_ya_cargada",
        )
    admins = await _usuarios(db, empresa_id, "admin")
    operadores = [u for u in await _usuarios(db, empresa_id, "encargado_sede", "usuario_inventario") if u.sede_id is not None]
    if not admins or not operadores:
        raise Conflicto(
            "Se necesita un administrador y al menos un encargado de sede o usuario de inventario con sede asignada.",
            codigo="demo_sig_faltan_usuarios",
        )
    admin = await _contexto(db, admins[0])
    ctx_operadores = [await _contexto(db, u) for u in operadores]
    autores = ctx_operadores + [await _contexto(db, u) for u in await _usuarios(db, empresa_id, "gerente", "analista_compras")]
    resultado = ResultadoDemoSig()

    informar("SIG · registrando solicitudes PQRS…")
    await _pqrs(db, autores, admin, resultado)
    informar("SIG · registrando entradas, no conformidades y garantías…")
    await _calidad(db, ctx_operadores, admin, resultado)
    informar("SIG · registrando el historial de pausas activas…")
    personas = [u for u in await _usuarios(db, empresa_id, "encargado_sede", "usuario_inventario", "gerente", "analista_compras") if sst_service.aplica_pausas(await _contexto(db, u))]
    await _pausas(db, admin, personas, resultado)
    informar("SIG · configurando la gestión ambiental con valores de demostración…")
    await _ambiental(db, admin, resultado)
    return resultado
