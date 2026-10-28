"""SIG · permisos al actualizar una instalación que ya existía (la base de la versión 1.0 no tenía los permisos del SIG)."""

from sqlalchemy import delete, select

from app.model.acceso import Permiso, Rol, RolPermiso
from app.security.permisos import PERMISOS, ROLES_POR_CLAVE
from app.service.bootstrap import sincronizar_permisos
from tests.ayuda import crear_empresa

CODIGOS_SIG = {p.codigo for p in PERMISOS if p.modulo.startswith("SIG")}


async def _permisos_de_roles(db) -> dict[str, set[str]]:
    filas = (await db.execute(select(Rol.clave, Rol.nombre, RolPermiso.permiso_codigo).join(RolPermiso, RolPermiso.rol_id == Rol.id))).all()
    resultado: dict[str, set[str]] = {}
    for clave, nombre, codigo in filas:
        resultado.setdefault(clave or f"personalizado:{nombre}", set()).add(codigo)
    return resultado


async def test_actualizar_una_instalacion_existente_reparte_los_permisos_del_sig(cliente, db):
    assert len(CODIGOS_SIG) == 9
    admin = await crear_empresa(db, cliente)
    r = await admin.post("/api/roles", {"nombre": "Auditor externo", "alcance": "empresa", "permisos": ["auditoria.ver"]})
    assert r.status_code == 201, r.text

    # Se reproduce la base de la versión 1.0: el catálogo y los roles todavía no conocen los permisos del SIG.
    await db.execute(delete(RolPermiso).where(RolPermiso.permiso_codigo.in_(CODIGOS_SIG)))
    await db.execute(delete(Permiso).where(Permiso.codigo.in_(CODIGOS_SIG)))
    await db.commit()
    assert not (CODIGOS_SIG & set().union(*(await _permisos_de_roles(db)).values()))

    # Lo que ocurre al arrancar la API con la versión 1.1.
    await sincronizar_permisos(db)
    await db.commit()

    por_rol = await _permisos_de_roles(db)
    for clave, definicion in ROLES_POR_CLAVE.items():
        assert por_rol[clave] & CODIGOS_SIG == definicion.permisos & CODIGOS_SIG, clave
    assert por_rol["admin"] >= CODIGOS_SIG  # el administrador tiene los nueve
    for clave in ("gerente", "encargado_sede", "usuario_inventario", "analista_compras"):
        assert {"pqrs.crear", "sst.ver", "calidad.ver", "ambiental.ver"} <= por_rol[clave], clave
        assert not (por_rol[clave] & {"pqrs.gestionar", "sst.gestionar", "calidad.gestionar", "ambiental.configurar"}), clave
    assert "calidad.reportar" in por_rol["encargado_sede"] and "calidad.reportar" in por_rol["usuario_inventario"]
    assert "calidad.reportar" not in por_rol["gerente"] and "calidad.reportar" not in por_rol["analista_compras"]
    # El rol creado por la empresa no recibe nada: su administrador decide.
    assert not (por_rol["personalizado:Auditor externo"] & CODIGOS_SIG)

    # Y funciona de verdad: un administrador ya puede gestionar PQRS y el catálogo expone los permisos nuevos.
    codigos = {p["codigo"] for p in (await admin.get("/api/permisos")).json()}
    assert CODIGOS_SIG <= codigos


async def test_sincronizar_de_nuevo_no_devuelve_un_permiso_que_la_empresa_quito(cliente, db):
    await crear_empresa(db, cliente)
    gerente = await db.scalar(select(Rol).where(Rol.clave == "gerente"))
    await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == gerente.id, RolPermiso.permiso_codigo == "ambiental.ver"))
    await db.commit()

    await sincronizar_permisos(db)  # no hay permisos nuevos: no se toca nada
    await db.commit()

    assert "ambiental.ver" not in (await _permisos_de_roles(db))["gerente"]
