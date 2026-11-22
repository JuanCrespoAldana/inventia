"""Migraciones de Alembic sobre PostgreSQL real (base vacía y base heredada con datos)."""

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

    r = _alembic(url, "upgrade", "0004_sig")  # el SIG se retira en 0006: aquí se prueba 0004 por separado
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


# --------------------------------------------------------------------------- 0005: integridad del MER (CRF-MER-01)
_BASE_0004 = (
    "INSERT INTO empresas(nombre) VALUES ('E')",
    "INSERT INTO sedes(empresa_id,nombre) VALUES (1,'Norte'),(1,'Sur')",
    "INSERT INTO categorias(empresa_id,nombre) VALUES (1,'C')",
    "INSERT INTO productos(empresa_id,nombre,categoria_id,codigo) VALUES (1,'P1',1,'P-1'),(1,'P2',1,'P-2')",
    "INSERT INTO roles(empresa_id,nombre) VALUES (1,'R')",
    "INSERT INTO usuarios(empresa_id,nombre,email,password_hash,activo,rol_id) VALUES (1,'A','a@e.com','x',true,1)",
    "INSERT INTO inventario_sede(empresa_id,sede_id,producto_id,cantidad,stock_minimo) VALUES (1,1,1,10,2)",
    "INSERT INTO ejecuciones_prediccion(empresa_id,usuario_id,estado,horizonte_dias,parametros,resumen) "
    "VALUES (1,1,'completada',30,'{}','{}')",
)


def _alerta(sede: int, producto: int) -> str:
    return (
        "INSERT INTO alertas(empresa_id,sede_id,producto_id,tipo,prioridad,estado,mensaje,detalle) "
        f"VALUES (1,{sede},{producto},'inventario_bajo','alta','activa','m','{{}}')"
    )


def _recomendacion(ejecucion: str = "1") -> str:
    return (
        "INSERT INTO recomendaciones(empresa_id,ejecucion_id,tipo,producto_id,sede_id,cantidad_sugerida,prioridad,estado,"
        f"resumen,justificacion) VALUES (1,{ejecucion},'traslado',1,1,5,'alta','pendiente','r','{{}}')"
    )


def _traslado(numero: int, recomendacion: str) -> str:
    return (
        "INSERT INTO traslados(empresa_id,numero,sede_origen_id,sede_destino_id,estado,solicitado_por,solicitado_en,"
        f"recomendacion_id) VALUES (1,{numero},2,1,'solicitado',1,now(),{recomendacion})"
    )


async def test_migracion_0005_aplica_las_tres_reglas_del_mer_y_se_revierte():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "0004_sig").returncode == 0
    # Una alerta con existencia y otra de un producto que la sede no maneja (dato derivado huérfano).
    await _ejecutar(url, *_BASE_0004, _alerta(1, 1), _alerta(2, 2), _recomendacion(), _traslado(1, "1"))

    r = _alembic(url, "upgrade", "0005_integridad_mer")
    assert r.returncode == 0, r.stderr[-2000:]
    # No borra datos de negocio: solo descarta la alerta huérfana.
    assert (await _consulta(url, "select sede_id, producto_id from alertas")) == [(1, 1)]
    assert (await _consulta(url, "select count(*) from traslados"))[0][0] == 1
    assert (await _consulta(url, "select count(*) from recomendaciones"))[0][0] == 1

    # RGN-13: una alerta pertenece a una existencia por sede.
    with pytest.raises(Exception, match="fk_alertas_sede_id_inventario_sede"):
        await _ejecutar(url, _alerta(1, 2))
    # RGN-23: una recomendación da lugar a lo sumo a un traslado.
    with pytest.raises(Exception, match="uq_traslados_recomendacion_id"):
        await _ejecutar(url, _traslado(2, "1"))
    # RGN-21: toda recomendación nace de una ejecución.
    with pytest.raises(Exception, match="ejecucion_id"):
        await _ejecutar(url, _recomendacion("NULL"))
    # Reversible: se restablecen las llaves anteriores y las reglas dejan de exigirse.
    r = _alembic(url, "downgrade", "0004_sig")
    assert r.returncode == 0, r.stderr[-2000:]
    await _ejecutar(url, _alerta(1, 2), _traslado(2, "1"), _recomendacion("NULL"))


async def test_migracion_0005_se_detiene_con_un_mensaje_si_los_datos_impiden_las_reglas():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "0004_sig").returncode == 0
    # Una recomendación con dos traslados y una alerta huérfana: nada debe modificarse.
    await _ejecutar(url, *_BASE_0004, _alerta(2, 2), _recomendacion(), _traslado(1, "1"), _traslado(2, "1"))
    r = _alembic(url, "upgrade", "0005_integridad_mer")
    assert r.returncode != 0
    assert "más de un traslado" in r.stderr and "#1 (2 traslados)" in r.stderr
    assert (await _consulta(url, "select count(*) from alertas"))[0][0] == 1  # no descartó nada
    assert (await _consulta(url, "select version_num from alembic_version")) == [("0004_sig",)]

    # Una recomendación sin ejecución también detiene la migración con su propio mensaje.
    await _ejecutar(url, "DELETE FROM traslados WHERE numero = 2", _recomendacion("NULL"))
    r = _alembic(url, "upgrade", "0005_integridad_mer")
    assert r.returncode != 0 and "sin ejecución de predicción" in r.stderr


# --------------------------------------------------------------------- 0006: retiro del SIG y de los agentes de IA
_TABLAS_RETIRADAS = {
    "pqrs", "pqrs_historial", "no_conformidades", "no_conformidad_historial", "garantias", "garantia_historial",
    "sig_adjuntos", "sst_configuracion", "sst_actividades", "sst_pausas", "amb_configuracion", "amb_categorias",
    "amb_registros", "entrada_observaciones", "api_keys",
}
_PERMISOS_RETIRADOS = ("pqrs.crear", "sst.ver", "calidad.gestionar", "ambiental.ver", "agentes.gestionar")


async def _tablas(url: str) -> set[str]:
    return {f[0] for f in await _consulta(url, "select tablename from pg_tables where schemaname='public'")}


async def test_migracion_0006_retira_el_sig_y_los_agentes_conserva_las_entradas_y_se_revierte():
    url = _url_migraciones()
    await _recrear_base(url)
    assert _alembic(url, "upgrade", "0004_sig").returncode == 0
    await _ejecutar(
        url,
        *_BASE_0004,
        "INSERT INTO entradas_inventario(empresa_id,sede_id,numero,motivo,usuario_id,fecha) VALUES (1,1,1,'compra',1,now())",
        "INSERT INTO movimientos(empresa_id,sede_id,producto_id,tipo,delta,saldo_anterior,saldo_posterior,usuario_id,fecha,"
        "entrada_id) VALUES (1,1,1,'entrada',10,0,10,1,now(),1)",
        "INSERT INTO entrada_observaciones(entrada_id,usuario_id,contenido) VALUES (1,1,'llegó con un golpe')",
        "INSERT INTO pqrs(empresa_id, numero, tipo, asunto, descripcion, usuario_id) VALUES (1, 1, 'queja', 'A', 'D', 1)",
        "INSERT INTO api_keys(empresa_id,nombre,prefijo,key_hash,alcances,creada_por) VALUES (1,'k','pre','h','[]',1)",
        *(f"INSERT INTO permisos(codigo,modulo,descripcion) VALUES ('{c}','m','d') ON CONFLICT DO NOTHING" for c in (*_PERMISOS_RETIRADOS, "ventas.ver")),
        "INSERT INTO rol_permisos(rol_id,permiso_codigo) VALUES (1,'pqrs.crear'),(1,'ventas.ver')",
    )
    assert _TABLAS_RETIRADAS <= await _tablas(url)

    r = _alembic(url, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-3000:]
    tablas = await _tablas(url)
    assert not (_TABLAS_RETIRADAS & tablas)
    # Quedan las 22 tablas de la versión 1.2.0 (más la de control de Alembic) y el esquema coincide con los modelos.
    assert len(tablas - {"alembic_version"}) == 22 and "entradas_inventario" in tablas
    assert _alembic(url, "check").returncode == 0
    # Las entradas y sus líneas se conservan; solo desaparece lo del SIG.
    assert (await _consulta(url, "select numero, motivo from entradas_inventario")) == [(1, "compra")]
    assert (await _consulta(url, "select entrada_id, delta from movimientos")) == [(1, 10)]
    # Los permisos que solo usaban el SIG y los agentes se retiran (con sus asignaciones); el resto se conserva.
    codigos = {f[0] for f in await _consulta(url, "select codigo from permisos")}
    assert "ventas.ver" in codigos and not (set(_PERMISOS_RETIRADOS) & codigos)
    assert (await _consulta(url, "select permiso_codigo from rol_permisos")) == [("ventas.ver",)]

    # Reversible: las estructuras vuelven vacías (los datos retirados no se recuperan) y lo conservado sigue igual.
    r = _alembic(url, "downgrade", "0005_integridad_mer")
    assert r.returncode == 0, r.stderr[-2000:]
    assert _TABLAS_RETIRADAS <= await _tablas(url)
    for tabla in sorted(_TABLAS_RETIRADAS):
        assert (await _consulta(url, f"select count(*) from {tabla}"))[0][0] == 0, tabla
    assert (await _consulta(url, "select count(*) from entradas_inventario"))[0][0] == 1
    # Los historiales vuelven a ser de solo inserción.
    await _ejecutar(url, "INSERT INTO pqrs(empresa_id, numero, tipo, asunto, descripcion, usuario_id) VALUES (1, 1, 'queja', 'A', 'D', 1)",
                    "INSERT INTO pqrs_historial(pqrs_id, usuario_id, evento, estado_nuevo) VALUES (1, 1, 'creacion', 'pendiente')")
    with pytest.raises(Exception, match="solo inserción"):
        await _ejecutar(url, "DELETE FROM pqrs_historial")
    # Y se puede volver a retirar: el ciclo completo es repetible y el esquema final coincide con los modelos.
    assert _alembic(url, "upgrade", "head").returncode == 0
    assert _alembic(url, "check").returncode == 0
    assert not (_TABLAS_RETIRADAS & await _tablas(url))
