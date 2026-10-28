"""Utilidades para armar escenarios en las pruebas (no son fixtures)."""

from dataclasses import dataclass, field

from httpx import AsyncClient

from app.model.sede import Sede
from app.service import setup_service

PASSWORD = "Clave#Segura1"


@dataclass
class Sesion:
    """Una persona autenticada contra la API."""

    cliente: AsyncClient
    token: str
    usuario: dict
    password: str = PASSWORD
    cabeceras: dict = field(init=False)

    def __post_init__(self):
        self.cabeceras = {"Authorization": f"Bearer {self.token}"}

    async def get(self, ruta, **kw):
        return await self.cliente.get(ruta, headers=self.cabeceras, **kw)

    async def post(self, ruta, json=None, **kw):
        return await self.cliente.post(ruta, json=json, headers=self.cabeceras, **kw)

    async def put(self, ruta, json=None, **kw):
        return await self.cliente.put(ruta, json=json, headers=self.cabeceras, **kw)

    async def patch(self, ruta, json=None, **kw):
        return await self.cliente.patch(ruta, json=json, headers=self.cabeceras, **kw)

    async def delete(self, ruta, **kw):
        return await self.cliente.delete(ruta, headers=self.cabeceras, **kw)


async def iniciar_sesion(cliente: AsyncClient, email: str, password: str = PASSWORD) -> Sesion:
    r = await cliente.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    return Sesion(cliente, cuerpo["access_token"], cuerpo["usuario"], password)


async def crear_empresa(db, cliente, nombre="Distribuidora Andina", correo="admin@andina.com", sufijo="1") -> Sesion:
    """Empresa + administrador (saltándose el token de setup) y devuelve al admin ya autenticado."""
    await setup_service.crear_empresa_con_admin(
        db, nombre=nombre, identificacion=f"900{sufijo}00000-1"[:12], direccion=None, ciudad="Bogotá",
        telefono=None, email_empresa=None, admin_nombre="Administrador Demo", admin_email=correo,
        admin_password=PASSWORD,
    )
    await db.commit()
    return await iniciar_sesion(cliente, correo)


async def crear_sede(admin: Sesion, nombre="Sede Norte", **extra) -> dict:
    r = await admin.post("/api/sedes", {"nombre": nombre, "ciudad": "Bogotá", **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def roles_por_clave(admin: Sesion) -> dict:
    r = await admin.get("/api/roles")
    assert r.status_code == 200, r.text
    return {rol["clave"]: rol for rol in r.json() if rol.get("clave")}


async def crear_usuario(admin: Sesion, rol_clave: str, email: str, sede_id: int | None = None,
                        nombre="Persona de Prueba") -> Sesion:
    roles = await roles_por_clave(admin)
    r = await admin.post("/api/usuarios", {
        "nombre": nombre, "email": email, "password": PASSWORD, "rol_id": roles[rol_clave]["id"],
        "sede_id": sede_id, "forzar_cambio_password": False,
    })
    assert r.status_code == 201, r.text
    return await iniciar_sesion(admin.cliente, email)


async def contar_sedes(db) -> int:
    from sqlalchemy import func, select

    return await db.scalar(select(func.count()).select_from(Sede))


async def crear_categoria(admin: Sesion, nombre="General") -> dict:
    r = await admin.post("/api/categorias", {"nombre": nombre})
    assert r.status_code == 201, r.text
    return r.json()


async def crear_producto(admin: Sesion, categoria_id: int, codigo="P-001", nombre="Producto de prueba", **extra) -> dict:
    r = await admin.post("/api/productos", {"codigo": codigo, "nombre": nombre, "categoria_id": categoria_id, **extra})
    assert r.status_code == 201, r.text
    return r.json()


async def entrada(sesion: Sesion, sede_id: int, lineas: dict[int, int], motivo="compra"):
    r = await sesion.post("/api/inventario/entradas", {
        "sede_id": sede_id, "motivo": motivo, "items": [{"producto_id": p, "cantidad": c} for p, c in lineas.items()],
    })
    assert r.status_code == 201, r.text
    return r.json()


async def existencias(sesion: Sesion, sede_id: int, producto_id: int) -> int:
    r = await sesion.get(f"/api/inventario?sede_id={sede_id}&tamano=100")
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json()["items"] if f["producto"]["id"] == producto_id)
    return fila["cantidad"]


# ------------------------------------------------------------------------------ historial de ventas
def patron_semanal(dias: int = 56, base: int = 3, pico: int = 8, semilla: int = 5) -> list[int]:
    """Ventas diarias con pico de fin de semana: lo bastante regulares para que el modelo las aprenda."""
    import numpy as np

    rng = np.random.default_rng(semilla)
    return [int(rng.poisson(base + (pico if i % 7 in (4, 5) else 0))) for i in range(dias)]


async def sembrar_historial(
    db, admin: Sesion, sede_id: int, producto_id: int, ventas_por_dia: list[int], *, stock_final: int = 10
) -> None:
    """Registra, con los servicios reales, una venta por cada día con unidades (el último día es AYER) y deja
    ``stock_final`` unidades en la sede. Las alertas no se recalculan en cada venta (solo al final)."""
    from datetime import timedelta

    from sqlalchemy import select

    from app.demo import SinAlertas, _momento
    from app.dto.ventas_dto import VentaCrear, VentaItemCrear
    from app.model.catalogo import Producto
    from app.model.enums import TipoMovimiento
    from app.model.usuario import Usuario
    from app.security.dependencias import contexto_de_usuario
    from app.service import inventario_service, ventas_service
    from app.service.inventario_service import Operacion
    from app.util.tiempo import hoy_local

    usuario = await db.scalar(
        select(Usuario).where(Usuario.id == admin.usuario["id"]).execution_options(populate_existing=True)
    )
    ctx = contexto_de_usuario(usuario)
    producto = await db.get(Producto, producto_id)
    inicio = hoy_local() - timedelta(days=len(ventas_por_dia))
    with SinAlertas():
        await inventario_service.aplicar_lote(
            db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, fecha=_momento(inicio, 7, 30),
            operaciones=[Operacion(sede_id, producto, sum(ventas_por_dia) + stock_final, TipoMovimiento.ENTRADA, "inventario_inicial", None)],
        )
        await db.commit()
        for i, unidades in enumerate(ventas_por_dia):
            if unidades > 0:
                await ventas_service.registrar_venta(
                    db, ctx,
                    VentaCrear(sede_id=sede_id, observacion=None,
                               items=[VentaItemCrear(producto_id=producto_id, cantidad=unidades, precio_unitario=1000)]),
                    fecha=_momento(inicio + timedelta(days=i), 12),
                )
