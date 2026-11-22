"""CRF-MER-01: tres reglas del modelo entidad-relación que ahora garantiza la base de datos por sí sola.

* RGN-13: una alerta pertenece a una existencia por sede (llave compuesta hacia ``inventario_sede``).
* RGN-23: una recomendación da lugar a lo sumo a un traslado (``traslados.recomendacion_id`` único).
* RGN-21: toda recomendación nace de una ejecución de predicción (``recomendaciones.ejecucion_id`` obligatorio).

Se prueban contra PostgreSQL real porque las restricciones las impone el motor, no la aplicación."""

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.model.empresa import Empresa
from app.model.inventario import Alerta
from app.model.operaciones import Traslado
from app.model.prediccion import Recomendacion
from app.util.tiempo import ahora_utc
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    entrada,
)
from tests.test_prediccion import ejecutar, escenario
from tests.test_recomendaciones import generar, listar

pytestmark = pytest.mark.postgres


async def test_una_alerta_solo_puede_pertenecer_a_una_existencia_por_sede(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    p = await crear_producto(admin, (await crear_categoria(admin))["id"], "A-1", "Arroz", costo=10, precio_venta=20)
    await entrada(admin, norte["id"], {p["id"]: 5})  # el producto tiene existencia en Norte, no en Sur
    empresa_id = await db.scalar(select(Empresa.id))

    def alerta(sede_id: int) -> Alerta:
        return Alerta(empresa_id=empresa_id, sede_id=sede_id, producto_id=p["id"], tipo="inventario_bajo",
                      prioridad="alta", estado="activa", mensaje="Prueba", detalle={})

    db.add(alerta(norte["id"]))
    await db.flush()  # con existencia por sede, la alerta es válida
    db.add(alerta(sur["id"]))
    with pytest.raises(IntegrityError, match="fk_alertas_sede_id_inventario_sede"):
        await db.flush()
    await db.rollback()


async def test_una_recomendacion_da_lugar_a_lo_sumo_a_un_traslado(cliente, db):
    admin, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    await generar(admin)
    rec = (await listar(admin))[0]
    assert (await admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})).status_code == 200
    original = await db.scalar(select(Traslado).where(Traslado.recomendacion_id == rec["id"]))
    assert original is not None

    db.add(Traslado(
        empresa_id=original.empresa_id, numero=original.numero + 100, sede_origen_id=original.sede_origen_id,
        sede_destino_id=original.sede_destino_id, estado="solicitado", solicitado_por=original.solicitado_por,
        solicitado_en=ahora_utc(), recomendacion_id=rec["id"],
    ))
    with pytest.raises(IntegrityError, match="uq_traslados_recomendacion_id"):
        await db.flush()
    await db.rollback()


async def test_toda_recomendacion_nace_de_una_ejecucion_de_prediccion(cliente, db):
    admin, norte, _sur, p1, *_ = await escenario(cliente, db)
    db.add(Recomendacion(
        empresa_id=await db.scalar(select(Empresa.id)), ejecucion_id=None, tipo="reabastecimiento", producto_id=p1["id"],
        sede_id=norte["id"], cantidad_sugerida=5, prioridad="alta", estado="pendiente", resumen="Sin ejecución",
        justificacion={},
    ))
    with pytest.raises(IntegrityError, match="ejecucion_id"):
        await db.flush()
    await db.rollback()


async def test_dos_aprobaciones_simultaneas_no_producen_un_error_de_integridad(cliente, db):
    """La aprobación reclama la recomendación con una actualización condicional ANTES de crear el traslado: de varias
    aprobaciones a la vez avanza una y las demás reciben un conflicto claro (409), nunca un error 500 por el único."""
    admin, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    await generar(admin)
    rec = (await listar(admin))[0]
    respuestas = await asyncio.gather(*[admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {}) for _ in range(6)])
    assert sorted(r.status_code for r in respuestas) == [200, 409, 409, 409, 409, 409], [r.text for r in respuestas]
    # Las demás pierden la carrera de dos formas, según si leyeron la fila antes o después de que la primera confirmara:
    # «estado_cambiado» (la actualización condicional no encontró la fila pendiente) o «estado_invalido» (ya la vieron aprobada).
    assert {r.json()["codigo"] for r in respuestas if r.status_code == 409} <= {"estado_cambiado", "estado_invalido"}
    assert await db.scalar(select(func.count()).select_from(Traslado).where(Traslado.recomendacion_id == rec["id"])) == 1
