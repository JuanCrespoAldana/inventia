"""Comandos de administración de Inventia.

    python -m app.cli inicializar --empresa "Mi Empresa" --admin-nombre "Nombre Apellido" --admin-correo yo@empresa.com
    python -m app.cli sincronizar-permisos
    python -m app.cli predecir [--empresa-id N] [--horizonte 14]
    python -m app.cli cargar-demo [--dias 120] [--con-prediccion] [--con-sig] [--en-empresa-existente]
    python -m app.cli cargar-demo-sig

La contraseña del administrador se lee de la variable ``INVENTIA_ADMIN_PASSWORD`` o se pide por
consola (sin eco). Nunca se pasa por argumentos para que no quede en el historial del terminal.
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select


async def _inicializar(args: argparse.Namespace) -> int:
    from app.config.database import fabrica_de_sesiones
    from app.dto.comunes_dto import validar_password_segura
    from app.exception.excepciones import ErrorNegocio
    from app.service import setup_service

    password = os.environ.get("INVENTIA_ADMIN_PASSWORD") or getpass.getpass("Contraseña del administrador: ")
    if not os.environ.get("INVENTIA_ADMIN_PASSWORD") and password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    try:
        validar_password_segura(password)
    except ValueError as exc:
        print(f"Contraseña no válida: {exc}", file=sys.stderr)
        return 1
    async with fabrica_de_sesiones()() as db:
        if await setup_service.hay_empresa(db):
            print("El sistema ya tiene una empresa configurada; no se creó nada.", file=sys.stderr)
            return 1
        try:
            empresa, admin = await setup_service.crear_empresa_con_admin(
                db, nombre=args.empresa, identificacion=args.identificacion, direccion=None, ciudad=args.ciudad,
                telefono=None, email_empresa=None, admin_nombre=args.admin_nombre, admin_email=args.admin_correo,
                admin_password=password,
            )
            await db.commit()
        except ErrorNegocio as exc:
            print(exc.mensaje, file=sys.stderr)
            return 1
    print(f"Empresa «{empresa.nombre}» creada. Administrador: {admin.email}")
    return 0


async def _sincronizar_permisos(_args: argparse.Namespace) -> int:
    from app.config.database import fabrica_de_sesiones
    from app.service.bootstrap import sincronizar_permisos

    async with fabrica_de_sesiones()() as db:
        await sincronizar_permisos(db)
        await db.commit()
    print("Catálogo de permisos sincronizado.")
    return 0


async def _predecir(args: argparse.Namespace) -> int:
    from app.config.database import fabrica_de_sesiones
    from app.exception.excepciones import ErrorNegocio
    from app.model.acceso import Rol
    from app.model.empresa import Empresa
    from app.model.usuario import Usuario
    from app.security.dependencias import contexto_de_usuario
    from app.service import prediccion_service

    codigo = 0
    async with fabrica_de_sesiones()() as db:
        consulta = select(Empresa.id, Empresa.nombre).where(Empresa.activa.is_(True))
        if args.empresa_id:
            consulta = consulta.where(Empresa.id == args.empresa_id)
        empresas = (await db.execute(consulta.order_by(Empresa.id))).all()
        for empresa_id, nombre in empresas:
            admin = await db.scalar(
                select(Usuario).join(Rol, Rol.id == Usuario.rol_id)
                .where(Usuario.empresa_id == empresa_id, Usuario.activo.is_(True), Rol.clave == "admin")
                .order_by(Usuario.id).limit(1).execution_options(populate_existing=True)
            )
            if admin is None:
                print(f"{nombre}: sin administrador activo; se omite.")
                continue
            try:
                ejecucion = await prediccion_service.solicitar(db, contexto_de_usuario(admin), args.horizonte)
            except ErrorNegocio as exc:
                print(f"{nombre}: {exc.mensaje}")
                codigo = 1
                continue
            await prediccion_service.ejecutar_en_segundo_plano(ejecucion.id)
            await db.refresh(ejecucion)
            r = ejecucion.resumen or {}
            print(f"{nombre}: {ejecucion.estado}; series con predicción {r.get('series_con_prediccion')}, "
                  f"omitidas {r.get('series_omitidas')}, WAPE global {r.get('wape_global')}, "
                  f"RMSE global {r.get('rmse_global')}, MAPE global {r.get('mape_global')}")
            if ejecucion.estado != "completada":
                codigo = 1
    return codigo


async def _cargar_demo_sig(_args: argparse.Namespace) -> int:
    from app import demo_sig
    from app.config.database import fabrica_de_sesiones
    from app.exception.excepciones import ErrorNegocio

    async with fabrica_de_sesiones()() as db:
        try:
            r = await demo_sig.cargar_demo_sig(db, avance=print)
        except ErrorNegocio as exc:
            print(exc.mensaje, file=sys.stderr)
            return 1
    print(
        f"\nListo: {r.pqrs} solicitudes PQRS, {r.entradas} entradas, {r.no_conformidades} no conformidades, "
        f"{r.garantias} garantías y {r.pausas} pausas activas registradas."
    )
    if r.ambiental_configurado:
        print(
            f"Gestión ambiental configurada con VALORES DE DEMOSTRACIÓN ({r.vehiculos_incorporados} líneas de ventas anteriores incorporadas). "
            "Reemplázalos por datos documentados antes de usar las cifras en un informe."
        )
    return 0


async def _cargar_demo(args: argparse.Namespace) -> int:
    from app import demo, demo_sig
    from app.config.database import fabrica_de_sesiones
    from app.exception.excepciones import ErrorNegocio
    from app.service import setup_service

    async with fabrica_de_sesiones()() as db:
        if not args.en_empresa_existente and await setup_service.hay_empresa(db) and not args.permitir_con_datos:
            print(
                "La base de datos ya contiene una empresa. Los datos de demostración son para una base vacía "
                "(o usa --en-empresa-existente para cargarlos en la empresa creada con la configuración inicial, "
                "o --permitir-con-datos para crear una empresa de demostración adicional).",
                file=sys.stderr,
            )
            return 1
        sufijo = ""
        if args.permitir_con_datos:
            sufijo = f".{os.urandom(2).hex()}"
        try:
            resultado = await demo.cargar_demo(
                db, dias=args.dias, semilla=args.semilla, sufijo=sufijo,
                en_empresa_existente=args.en_empresa_existente, avance=print,
            )
            if args.con_prediccion:
                await demo.preparar_prediccion(db, resultado, print)
            if args.con_sig:
                await demo_sig.cargar_demo_sig(db, empresa_id=resultado.empresa_id, avance=print)
        except ErrorNegocio as exc:
            print(exc.mensaje, file=sys.stderr)
            return 1
    print(f"\nListo: {resultado.ventas} ventas entre {resultado.desde} y {resultado.hasta}.")
    if args.en_empresa_existente:
        print("El administrador de la empresa conserva su correo y su contraseña.")
    print("Credenciales de los usuarios de ejemplo (se muestran una sola vez; guárdalas):")
    for rol, correo, clave in resultado.credenciales:
        print(f"  {rol:<24} {correo:<44} {clave}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Administración de Inventia")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("inicializar", help="Crea la primera empresa y su administrador")
    p.add_argument("--empresa", required=True)
    p.add_argument("--admin-nombre", required=True)
    p.add_argument("--admin-correo", required=True)
    p.add_argument("--identificacion")
    p.add_argument("--ciudad")
    p.set_defaults(accion=_inicializar)

    p = sub.add_parser("sincronizar-permisos", help="Actualiza el catálogo de permisos con el del código")
    p.set_defaults(accion=_sincronizar_permisos)

    p = sub.add_parser("predecir", help="Genera la predicción de demanda (útil para tareas programadas)")
    p.add_argument("--empresa-id", type=int)
    p.add_argument("--horizonte", type=int)
    p.set_defaults(accion=_predecir)

    p = sub.add_parser("cargar-demo", help="Carga una empresa ficticia con historial de ventas")
    p.add_argument("--dias", type=int, default=120)
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--con-prediccion", action="store_true", help="Además genera la predicción y las recomendaciones")
    p.add_argument("--con-sig", action="store_true", help="Además carga datos de ejemplo del módulo SIG (PQRS, calidad, SST y gestión ambiental)")
    p.add_argument("--permitir-con-datos", action="store_true")
    p.add_argument(
        "--en-empresa-existente", action="store_true",
        help="Carga los datos en la empresa creada con la configuración inicial (conserva a su administrador)",
    )
    p.set_defaults(accion=_cargar_demo)

    p = sub.add_parser("cargar-demo-sig", help="Carga datos de ejemplo del módulo SIG en la empresa existente (PQRS, calidad, SST y ambiental)")
    p.set_defaults(accion=_cargar_demo_sig)

    args = parser.parse_args(argv)
    if args.comando == "predecir" and args.horizonte is not None and not 1 <= args.horizonte <= 90:
        parser.error("--horizonte debe estar entre 1 y 90")
    if args.comando == "cargar-demo" and not 60 <= args.dias <= 365:
        parser.error("--dias debe estar entre 60 y 365")
    if args.comando == "cargar-demo" and args.en_empresa_existente and args.permitir_con_datos:
        parser.error("--en-empresa-existente y --permitir-con-datos no se pueden usar juntos")
    return asyncio.run(args.accion(args))


if __name__ == "__main__":
    raise SystemExit(main())
