"""Datos de demostración: carga en la empresa creada con la configuración inicial (--en-empresa-existente)."""

import pytest
from sqlalchemy import func, select

from app import cli, demo, demo_sig
from app.exception.excepciones import Conflicto
from app.model.ambiental import AmbRegistro
from app.model.calidad import Garantia, NoConformidad
from app.model.catalogo import Producto
from app.model.empresa import Empresa
from app.model.inventario import EntradaInventario
from app.model.pqrs import Pqrs
from app.model.sede import Sede
from app.model.sst import SstPausa
from app.model.usuario import Usuario
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


async def test_la_demo_del_sig_carga_datos_coherentes_y_no_se_duplica(cliente, db):
    await crear_empresa(db, cliente, correo="duena@empresa.example")
    await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)

    r = await demo_sig.cargar_demo_sig(db)

    contar = lambda modelo: db.scalar(select(func.count()).select_from(modelo))  # noqa: E731
    assert (await contar(Pqrs), await contar(NoConformidad), await contar(Garantia)) == (r.pqrs, r.no_conformidades, r.garantias) == (5, 3, 3)
    assert await contar(EntradaInventario) == r.entradas == 2
    assert await contar(SstPausa) == r.pausas > 0
    # La primera no conformidad nace de una observación de la entrada y no cambió el inventario por sí sola.
    nc = await db.scalar(select(NoConformidad).where(NoConformidad.numero == 1))
    assert nc.entrada_id is not None and nc.entrada_observacion_id is not None

    # Las pausas son solo de personas a las que aplican: la administración queda fuera.
    admin = await db.scalar(select(Usuario).where(Usuario.email == "duena@empresa.example"))
    assert not await db.scalar(select(func.count()).select_from(SstPausa).where(SstPausa.usuario_id == admin.id))

    # Gestión ambiental: las ventas previas a la configuración se incorporan y quedan calculadas con parámetros rotulados.
    assert r.ambiental_configurado and r.vehiculos_incorporados > 0
    assert await contar(AmbRegistro) == r.vehiculos_incorporados
    assert not await db.scalar(select(func.count()).select_from(AmbRegistro).where(AmbRegistro.co2_evitado_kg.is_(None)))
    assert "DEMOSTRACIÓN" in demo_sig.FUENTE_DEMO and "DEMOSTRACIÓN" in demo_sig.FUENTE_FACTOR_DEMO

    # Cargarla de nuevo no duplica nada.
    with pytest.raises(Conflicto) as repetida:
        await demo_sig.cargar_demo_sig(db)
    assert repetida.value.codigo == "demo_sig_ya_cargada"
    await db.rollback()
    assert await contar(Pqrs) == 5


async def test_la_demo_del_sig_exige_usuarios_operativos(cliente, db):
    await crear_empresa(db, cliente)
    with pytest.raises(Conflicto) as error:
        await demo_sig.cargar_demo_sig(db)
    assert error.value.codigo == "demo_sig_faltan_usuarios"
