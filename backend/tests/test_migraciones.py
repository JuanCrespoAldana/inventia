"""Migraciones de Alembic sobre PostgreSQL real (base vacía y base heredada con datos)."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import URL_PRUEBA

pytestmark = pytest.mark.postgres
RAIZ = Path(__file__).resolve().parents[1]


def _url_migraciones() -> str:
    """Base DESCARTABLE distinta de la de pruebas (se recrea en cada ejecución)."""
    base = make_url(URL_PRUEBA)
    return base.set(database=base.database + "_migraciones").render_as_string(hide_password=False)


async def _recrear_base(url: str) -> None:
    u = make_url(url)
    admin = create_async_engine(u.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin.connect() as c:
        await c.execute(text(f'DROP DATABASE IF EXISTS "{u.database}" WITH (FORCE)'))
        await c.execute(text(f'CREATE DATABASE "{u.database}"'))
    await admin.dispose()


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess:
    entorno = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=300
    )


async def _consulta(url: str, sql: str):
    motor = create_async_engine(url)
    try:
        async with motor.connect() as c:
            return (await c.execute(text(sql))).all()
    finally:
        await motor.dispose()


async def _ejecutar(url: str, *sentencias: str):
    motor = create_async_engine(url)
    try:
        async with motor.begin() as c:
            for sql in sentencias:
                await c.execute(text(sql))
    finally:
        await motor.dispose()


async def test_migracion_desde_base_vacia_y_alembic_check():
    url = _url_migraciones()
    await _recrear_base(url)
    r = _alembic(url, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-2000:]
    r = _alembic(url, "check")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    tablas = {f[0] for f in await _consulta(url, "select tablename from pg_tables where schemaname='public'")}
    assert {"empresas", "sedes", "usuarios", "roles", "permisos", "productos", "inventario_sede", "movimientos",
            "ventas", "traslados", "alertas", "auditoria", "predicciones", "recomendaciones"} <= tablas


async def test_migracion_hacia_atras_y_adelante():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "head").returncode == 0
    r = _alembic(url, "downgrade", "5cb4ddecc152")
    assert r.returncode == 0, r.stderr[-2000:]
    r = _alembic(url, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-2000:]


async def test_migracion_conserva_datos_de_la_version_anterior():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "5cb4ddecc152").returncode == 0
    await _ejecutar(
        url,
        "INSERT INTO empresas(nombre) VALUES ('Empresa Heredada')",
        "INSERT INTO sedes(empresa_id,nombre,ciudad) VALUES (1,'Norte','Bogotá'),(1,'NORTE','Cali'),(1,'Sur','Cali')",
        "INSERT INTO productos(empresa_id,sku,nombre,precio) VALUES (1,'A-1','Tornillo',150.5),(1,'A-2','Tuerca',NULL)",
        "INSERT INTO inventario_sede(sede_id,producto_id,cantidad,stock_minimo) VALUES (1,1,100,10),(3,1,0,5),(3,2,-4,2)",
        "INSERT INTO usuarios(empresa_id,sede_id,nombre,email,password_hash,rol,activo) VALUES "
        "(1,NULL,'Admin','Admin@Heredada.com','x','ADMIN_GENERAL',true),"
        "(1,1,'Operario','op@heredada.com','x','USUARIO_SEDE',true),"
        "(1,NULL,'Sin sede','sinsede@heredada.com','x','USUARIO_SEDE',true)",
    )
    r = _alembic(url, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-3000:]

    usuarios = await _consulta(url, "select u.email, r.clave, u.activo from usuarios u join roles r on r.id=u.rol_id order by u.id")
    assert usuarios == [("admin@heredada.com", "admin", True), ("op@heredada.com", "usuario_inventario", True),
                        ("sinsede@heredada.com", "usuario_inventario", False)]
    sedes = await _consulta(url, "select count(distinct lower(nombre)) from sedes")
    assert sedes[0][0] == 3  # el nombre repetido se desambiguó
    prod = await _consulta(url, "select codigo, precio_venta from productos order by id")
    assert [p[0] for p in prod] == ["A-1", "A-2"] and float(prod[0][1]) == 150.5
    # El historial cuadra con las existencias: suma(movimientos) = cantidad, y no hay negativas.
    descuadres = await _consulta(
        url,
        "select i.id from inventario_sede i left join (select sede_id, producto_id, sum(delta) d from movimientos group by 1,2) m "
        "on m.sede_id=i.sede_id and m.producto_id=i.producto_id where coalesce(m.d,0) <> i.cantidad",
    )
    assert descuadres == []
    assert (await _consulta(url, "select min(cantidad) from inventario_sede"))[0][0] == 0
    # Roles y permisos creados para la empresa.
    assert (await _consulta(url, "select count(*) from roles"))[0][0] == 5
    assert (await _consulta(url, "select count(*) from rol_permisos rp join roles r on r.id=rp.rol_id where r.clave='admin'"))[0][0] >= 40


async def test_auditoria_y_movimientos_son_de_solo_insercion():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "head").returncode == 0
    await _ejecutar(
        url,
        "INSERT INTO empresas(nombre) VALUES ('E')",
        "INSERT INTO auditoria(empresa_id, modulo, accion, resultado, detalle, fecha) VALUES (1,'m','a','ok','{}', now())",
    )
    with pytest.raises(Exception, match="solo inserción"):
        await _ejecutar(url, "UPDATE auditoria SET accion='x'")
    with pytest.raises(Exception, match="solo inserción"):
        await _ejecutar(url, "DELETE FROM auditoria")


async def test_migracion_del_sig_conserva_datos_se_revierte_y_protege_historiales():
    """0004_sig solo agrega: no toca lo existente, se puede deshacer y los historiales nuevos no se pueden alterar."""
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "5cb4ddecc152").returncode == 0
    await _ejecutar(
        url,
        "INSERT INTO empresas(nombre) VALUES ('Empresa Heredada')",
        "INSERT INTO sedes(empresa_id,nombre,ciudad) VALUES (1,'Norte','Bogotá')",
        "INSERT INTO productos(empresa_id,sku,nombre,precio) VALUES (1,'A-1','Tornillo',150.5)",
        "INSERT INTO inventario_sede(sede_id,producto_id,cantidad,stock_minimo) VALUES (1,1,100,10)",
        "INSERT INTO usuarios(empresa_id,sede_id,nombre,email,password_hash,rol,activo) VALUES "
        "(1,NULL,'Admin','admin@heredada.com','x','ADMIN_GENERAL',true)",
    )
    assert _alembic(url, "upgrade", "0003_inventia").returncode == 0
    antes = await _consulta(url, "select count(*), coalesce(sum(delta),0) from movimientos")

    r = _alembic(url, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-2000:]
    assert await _consulta(url, "select count(*), coalesce(sum(delta),0) from movimientos") == antes
    assert (await _consulta(url, "select count(*) from movimientos where entrada_id is not null"))[0][0] == 0
    tablas_sig = {"entradas_inventario", "entrada_observaciones", "pqrs", "pqrs_historial", "no_conformidades",
                  "no_conformidad_historial", "garantias", "garantia_historial", "sig_adjuntos", "sst_configuracion",
                  "sst_actividades", "sst_pausas", "amb_configuracion", "amb_categorias", "amb_registros"}
    existentes = {f[0] for f in await _consulta(url, "select tablename from pg_tables where schemaname='public'")}
    assert tablas_sig <= existentes

    # Historiales de solo inserción: se puede agregar, no editar ni borrar.
    await _ejecutar(
        url,
        "INSERT INTO pqrs(empresa_id, numero, tipo, asunto, descripcion, usuario_id) "
        "VALUES (1, 1, 'queja', 'Asunto', 'Descripción', 1)",
        "INSERT INTO pqrs_historial(pqrs_id, usuario_id, evento, estado_nuevo) VALUES (1, 1, 'creacion', 'pendiente')",
    )
    with pytest.raises(Exception, match="solo inserción"):
        await _ejecutar(url, "UPDATE pqrs_historial SET comentario='alterado'")
    with pytest.raises(Exception, match="solo inserción"):
        await _ejecutar(url, "DELETE FROM pqrs_historial")
    # Una evidencia pertenece a un único registro.
    with pytest.raises(Exception, match="un_solo_destino"):
        await _ejecutar(
            url,
            "INSERT INTO sig_adjuntos(empresa_id, nombre, tipo_mime, tamano, sha256, contenido, subido_por) "
            "VALUES (1, 'a.pdf', 'application/pdf', 3, 'x', 'abc', 1)",
        )
    # Una persona no puede tener dos pausas abiertas.
    await _ejecutar(
        url,
        "INSERT INTO sst_pausas(empresa_id, usuario_id, actividad_titulo, mostrada_en, estado) VALUES (1, 1, 'Cuello', now(), 'mostrada')",
    )
    with pytest.raises(Exception, match="uq_sst_pausa_abierta"):
        await _ejecutar(
            url,
            "INSERT INTO sst_pausas(empresa_id, usuario_id, actividad_titulo, mostrada_en, estado) VALUES (1, 1, 'Ojos', now(), 'mostrada')",
        )

    # Deshacer solo el SIG: las tablas desaparecen y lo anterior queda intacto.
    r = _alembic(url, "downgrade", "0003_inventia")
    assert r.returncode == 0, r.stderr[-2000:]
    existentes = {f[0] for f in await _consulta(url, "select tablename from pg_tables where schemaname='public'")}
    assert not (tablas_sig & existentes)
    assert await _consulta(url, "select count(*), coalesce(sum(delta),0) from movimientos") == antes
    columnas = {f[0] for f in await _consulta(url, "select column_name from information_schema.columns where table_name='movimientos'")}
    assert "entrada_id" not in columnas
    assert _alembic(url, "upgrade", "head").returncode == 0
    assert _alembic(url, "check").returncode == 0
