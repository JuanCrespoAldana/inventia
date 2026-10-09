"""Datos de demostración: carga en la empresa creada con la configuración inicial (--en-empresa-existente)."""

import pytest
from sqlalchemy import func, select

from app import cli, demo
from app.core.exceptions import Conflicto
from app.models.catalogo import Producto
from app.models.empresa import Empresa
from app.models.sede import Sede
from app.models.usuario import Usuario
from tests.ayuda import PASSWORD, crear_empresa, iniciar_sesion

DIAS = 60  # el mínimo permitido
PRODUCTOS = 6  # una parte del catálogo basta para la prueba y la hace rápida


async def test_la_demo_se_carga_en_la_empresa_existente_y_el_administrador_conserva_su_acceso(cliente, db):
    await crear_empresa(db, cliente, nombre="Mi Empresa de Prueba", correo="duena@empresa.example")

    resultado = await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)

    empresa = await db.scalar(select(Empresa))
    assert resultado.empresa_id == empresa.id
    assert empresa.nombre == "Mi Empresa de Prueba"  # no se crea otra empresa ni se renombra
    assert await db.scalar(select(func.count()).select_from(Empresa)) == 1
    assert await db.scalar(select(func.count()).select_from(Sede).where(Sede.empresa_id == empresa.id)) == 3
    assert await db.scalar(select(func.count()).select_from(Producto).where(Producto.empresa_id == empresa.id)) == PRODUCTOS
    assert resultado.ventas > 0

    # Solo se generan credenciales para los usuarios de ejemplo: ninguna es la del administrador real.
    correos = {correo for _rol, correo, _clave in resultado.credenciales}
    assert "duena@empresa.example" not in correos
    assert len(correos) == 6 and all(c.endswith("@demo.inventia.example") for c in correos)
    assert not any(rol == "Administrador" for rol, _c, _k in resultado.credenciales)

    # El administrador sigue entrando con su propia contraseña y ve los datos cargados.
    admin = await iniciar_sesion(cliente, "duena@empresa.example", PASSWORD)
    r = await admin.get("/api/sedes")
    assert r.status_code == 200
    assert r.json()["total"] == 3

    # Un usuario de ejemplo también puede entrar con la contraseña que se mostró.
    rol, correo, clave = next(c for c in resultado.credenciales if c[1].startswith("gerente"))
    gerente = await iniciar_sesion(cliente, correo, clave)
    assert gerente.usuario["rol"]["nombre"] == rol


async def test_la_demo_no_se_carga_dos_veces_en_la_misma_empresa(cliente, db):
    await crear_empresa(db, cliente)
    await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)
    antes = await db.scalar(select(func.count()).select_from(Usuario))

    with pytest.raises(Conflicto) as error:
        await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)

    assert error.value.codigo == "demo_empresa_con_datos"
    await db.rollback()
    assert await db.scalar(select(func.count()).select_from(Usuario)) == antes


async def test_la_demo_en_empresa_existente_exige_exactamente_una_empresa(cliente, db):
    with pytest.raises(Conflicto) as sin_empresa:
        await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)
    assert sin_empresa.value.codigo == "demo_empresa_no_unica"

    await crear_empresa(db, cliente, nombre="Primera", correo="uno@empresa.example", sufijo="1")
    await crear_empresa(db, cliente, nombre="Segunda", correo="dos@empresa.example", sufijo="2")
    with pytest.raises(Conflicto) as dos_empresas:
        await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)
    assert dos_empresas.value.codigo == "demo_empresa_no_unica"


def test_el_cli_no_acepta_a_la_vez_empresa_existente_y_empresa_adicional(capsys):
    with pytest.raises(SystemExit) as salida:
        cli.main(["cargar-demo", "--en-empresa-existente", "--permitir-con-datos"])
    assert salida.value.code == 2
    assert "no se pueden usar juntos" in capsys.readouterr().err
