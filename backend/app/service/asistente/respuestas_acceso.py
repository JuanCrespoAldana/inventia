"""Respuestas sobre los accesos de los usuarios y sobre quién puede hacer qué (permisos por rol)."""

import re

from sqlalchemy import select

from app.model.acceso import Rol
from app.model.usuario import Usuario
from app.security.permisos import PERMISOS
from app.service.asistente import bloques as B
from app.service.asistente.datos import enlaces_a
from app.service.asistente.peticion import Peticion, manejador
from app.util import lenguaje as L
from app.util.tiempo import a_fecha_local, ahora_utc, fin_de_dia_utc, inicio_de_dia_utc


# ===================================================================================================== accesos de usuarios
@manejador("usuarios_acceso")
async def usuarios_acceso(p: Peticion) -> B.Resp:
    f = p.frase
    cond = [Usuario.empresa_id == p.ctx.empresa_id]
    if p.sede_ids is not None:
        cond.append(Usuario.sede_id.in_(p.sede_ids))
    ahora = ahora_utc()
    if re.search(r"\bbloquead\w+\b", f):
        filas = (await p.db.scalars(select(Usuario).where(*cond, Usuario.bloqueado_hasta.is_not(None), Usuario.bloqueado_hasta > ahora).order_by(Usuario.nombre))).all()
        if not filas:
            return B.Resp("No hay usuarios bloqueados en este momento.", enlaces=enlaces_a(p, "/usuarios"), sugerencias=["¿Cuántos usuarios hay?"])
        return B.Resp(f"Hay **{B.n_de(len(filas), 'usuario')} bloqueado{'' if len(filas) == 1 else 's'}** por intentos fallidos de ingreso: " + B.lista_natural([u.nombre for u in filas]) + ".", enlaces=enlaces_a(p, "/usuarios"))
    if p.periodo:
        cond += [Usuario.ultimo_acceso >= inicio_de_dia_utc(p.periodo.desde), Usuario.ultimo_acceso < fin_de_dia_utc(p.periodo.hasta)]
    else:
        cond.append(Usuario.ultimo_acceso.is_not(None))
    filas = (await p.db.scalars(select(Usuario).where(*cond).order_by(Usuario.ultimo_acceso.desc()).limit(p.limite(10)))).all()
    if not filas:
        return B.Resp(f"Ninguna persona ingresó al sistema {p.en_periodo(p.periodo) if p.periodo else 'según los registros'}.", enlaces=enlaces_a(p, "/usuarios"), sugerencias=["Actividad reciente de los usuarios"])
    roles = {r.id: r.nombre for r in (await p.db.scalars(select(Rol).where(Rol.empresa_id == p.ctx.empresa_id))).all()}
    primero = filas[0]
    texto = f"{'El último ingreso fue de' if not p.periodo else 'Ingresaron ' + B.n_de(len(filas), 'persona') + ' ' + p.en_periodo(p.periodo) + '. El más reciente:'} **{primero.nombre}** el {L.fecha_larga(a_fecha_local(primero.ultimo_acceso))}."
    tabla = B.tabla(None, [B.col("nombre", "Persona"), B.col("rol", "Rol"), B.col("acceso", "Último ingreso", "fecha_hora")],
                    [B.fila({"nombre": u.nombre, "rol": roles.get(u.rol_id, "—"), "acceso": u.ultimo_acceso}, ruta="/usuarios") for u in filas])
    return B.Resp(texto, [tabla], enlaces_a(p, "/usuarios", "/auditoria"), ["Actividad reciente de los usuarios", "¿Cuántos usuarios hay?"], ["Se muestra el último ingreso de cada persona, no cada sesión."])


# ======================================================================================================== quién puede qué
_ACCIONES: tuple[tuple[re.Pattern, str, str], ...] = tuple((re.compile(r), c, t) for r, c, t in (
    (r"\banul\w+\b.*\bventa|\bventa\w*\b.*\banul", "ventas.anular", "anular ventas"),
    (r"\b(registr\w+|hacer|crear|realizar|emitir)\b.*\bventa", "ventas.registrar", "registrar ventas"),
    (r"\bver\b.*\bventa|\bconsultar\b.*\bventa", "ventas.ver", "ver las ventas"),
    (r"\baprob\w+\b.*\btraslad", "traslados.aprobar", "aprobar traslados"),
    (r"\bconfirm\w+\b.*\btraslad|\brecib\w+\b.*\btraslad", "traslados.confirmar", "confirmar traslados"),
    (r"\b(solicit\w+|crear|hacer|pedir)\b.*\btraslad", "traslados.solicitar", "solicitar traslados"),
    (r"\bajust\w+\b.*\b(inventario|stock|existencias)|\bajustes?\b", "inventario.ajustar", "ajustar el inventario"),
    (r"\b(registr\w+|dar|hacer)\b.*\bentradas?\b|\bingres\w+ (de )?mercancia|\brecib\w+ mercancia", "inventario.entrada", "registrar entradas de mercancía"),
    (r"\b(registr\w+|dar|hacer)\b.*\bsalidas?\b|\bmermas?\b", "inventario.salida", "registrar salidas y mermas"),
    (r"\b(niveles|stock minimo|stock maximo|minimos?|maximos?)\b", "inventario.niveles", "configurar los niveles mínimo y máximo"),
    (r"\bcrear\b.*\bproducto|\bagregar\b.*\bproducto|\bnuevo producto", "productos.crear", "crear productos"),
    (r"\bedit\w+\b.*\bproducto|\bmodificar\b.*\bproducto", "productos.editar", "editar productos"),
    (r"\b(inhabilit\w+|desactiv\w+|deshabilit\w+)\b.*\bproducto", "productos.inhabilitar", "inhabilitar productos"),
    (r"\bcrear\b.*\busuario|\bagregar\b.*\busuario|\bnuevo usuario", "usuarios.crear", "crear usuarios"),
    (r"\bedit\w+\b.*\busuario|\bcambiar\b.*\busuario", "usuarios.editar", "editar usuarios"),
    (r"\b(inhabilit\w+|desactiv\w+|deshabilit\w+|bloquear)\b.*\busuario", "usuarios.inhabilitar", "inhabilitar usuarios"),
    (r"\basignar\b.*\bpermiso|\bpermisos? (de|a) (un )?rol", "roles.asignar_permisos", "asignar permisos a los roles"),
    (r"\bcrear\b.*\brol\b|\bnuevo rol\b", "roles.crear", "crear roles"),
    (r"\b(ejecutar|generar|correr|lanzar|hacer)\b.*\bprediccion|\bprediccion\b.*\b(ejecutar|generar)", "prediccion.ejecutar", "ejecutar la predicción"),
    (r"\baprob\w+\b.*\brecomend\w+|\brechaz\w+\b.*\brecomend\w+", "recomendaciones.aprobar", "aprobar o rechazar recomendaciones"),
    (r"\b(generar|calcular|crear)\b.*\brecomend\w+", "recomendaciones.generar", "generar recomendaciones"),
    (r"\brecalcular\b.*\balert\w+|\balert\w+\b.*\brecalcular", "alertas.recalcular", "recalcular alertas"),
    (r"\b(ver|consultar|revisar)\b.*\bauditoria|\bauditoria\b", "auditoria.ver", "consultar la auditoría"),
    (r"\bedit\w+\b.*\bempresa|\bparametros?\b", "empresa.editar", "editar los datos y parámetros de la empresa"),
    (r"\bcrear\b.*\bsede|\bnueva sede", "sedes.crear", "crear sedes"),
    (r"\bedit\w+\b.*\bsede", "sedes.editar", "editar sedes"),
    (r"\bcrear\b.*\bcategoria|\bnueva categoria", "categorias.crear", "crear categorías"),
    (r"\b(descargar|exportar|sacar|generar)\b.*\breporte|\breportes?\b", "reportes.ventas", "descargar reportes"),
    (r"\bconsolidado\b", "inventario.consolidado", "ver el inventario consolidado de todas las sedes"),
))
_PREGUNTA_PROPIA = re.compile(r"\b(puedo|podria|me deja|me permite|me permiten|tengo permiso|tengo acceso|estoy autorizad\w+|mi rol puede|puede mi rol)\b")


@manejador("permiso_quien")
async def permiso_quien(p: Peticion) -> B.Resp:
    f = p.frase
    accion = next(((c, t) for rx, c, t in _ACCIONES if rx.search(f)), None)
    if accion is None:
        return B.Resp("¿Qué acción quieres saber? Por ejemplo: «¿Quién puede anular ventas?», «¿Puedo aprobar traslados?» o «¿Qué rol puede crear usuarios?».",
                      sugerencias=["¿Quién puede anular ventas?", "¿Puedo aprobar traslados?", "¿Qué roles hay?"], entendida=False)
    codigo, texto_accion = accion
    definicion = next((d for d in PERMISOS if d.codigo == codigo), None)
    yo = p.tiene(codigo)
    propia = bool(_PREGUNTA_PROPIA.search(f))
    puede_ver_roles = p.tiene("roles.ver", "usuarios.ver")
    con_rol: list[Rol] = []
    if puede_ver_roles:
        roles = (await p.db.scalars(select(Rol).where(Rol.empresa_id == p.ctx.empresa_id, Rol.activo.is_(True)).order_by(Rol.nombre))).all()
        con_rol = [r for r in roles if codigo in r.codigos_permisos]
    partes = []
    if propia or not puede_ver_roles:
        partes.append(f"**{'Sí' if yo else 'No'}**, con tu rol ({p.ctx.rol.nombre}) {'puedes' if yo else 'no puedes'} {texto_accion}.")
    if con_rol:
        nombres = [r.nombre for r in con_rol]
        partes.append(f"{'Pueden' if len(nombres) > 1 else 'Puede'} {texto_accion}: {B.lista_natural(nombres)}.")
    elif puede_ver_roles:
        partes.append(f"Ningún rol activo tiene permiso para {texto_accion}.")
    bloques = []
    if con_rol and p.tiene("usuarios.ver"):
        cond = [Usuario.empresa_id == p.ctx.empresa_id, Usuario.rol_id.in_([r.id for r in con_rol]), Usuario.activo.is_(True)]
        if p.sede_ids is not None:
            cond.append(Usuario.sede_id.in_(p.sede_ids))
        personas = (await p.db.scalars(select(Usuario).where(*cond).order_by(Usuario.nombre).limit(15))).all()
        if personas:
            nombre_rol = {r.id: r.nombre for r in con_rol}
            bloques.append(B.tabla("Personas con ese permiso", [B.col("nombre", "Persona"), B.col("rol", "Rol")], [B.fila({"nombre": u.nombre, "rol": nombre_rol.get(u.rol_id, "—")}, ruta="/usuarios") for u in personas]))
    avisos = [f"Permiso del sistema: «{definicion.descripcion}»."] if definicion else []
    return B.Resp(" ".join(partes), bloques, enlaces_a(p, "/roles", "/usuarios"), ["¿Qué roles hay?", "¿Cuáles son mis permisos?"], avisos)
