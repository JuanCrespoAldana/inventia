"""Respuestas ampliadas de calidad, PQRS, gestión ambiental, usuarios y permisos."""

import re
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func, select

from app.model.acceso import Rol
from app.model.ambiental import AmbRegistro
from app.model.calidad import Garantia, NoConformidad
from app.model.catalogo import Producto
from app.model.pqrs import Pqrs
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.security.permisos import PERMISOS
from app.service.asistente import bloques as B
from app.service.asistente.analisis import nombre_producto, nota_listado
from app.service.asistente.datos import enlaces_a
from app.service.asistente.peticion import Peticion, manejador
from app.util import lenguaje as L
from app.util.tiempo import a_fecha_local, ahora_utc, asegurar_utc, fin_de_dia_utc, inicio_de_dia_utc

_ABIERTA_NC = ("reportado", "en_revision", "en_proceso_solucion")
_ABIERTA_GARANTIA = ("reportada", "pendiente_revision", "enviada_proveedor")
KG_CO2_POR_ARBOL_AL_ANIO = 21  # referencia de uso común (≈21 kg de CO₂ absorbidos por un árbol adulto en un año); no es un dato de la empresa


def _dias(desde, hasta) -> float:
    return (asegurar_utc(hasta) - asegurar_utc(desde)).total_seconds() / 86400


def _duracion(dias: float) -> str:
    if dias * 24 < 1:
        return "menos de 1 hora"
    if dias < 1:
        return f"{B.decimal(dias * 24, 1)} horas"
    return f"{B.decimal(dias, 1)} días"


# ================================================================================================= análisis de calidad
@manejador("calidad_analisis")
async def calidad_analisis(p: Peticion) -> B.Resp:
    f = p.frase
    sede_nc = [NoConformidad.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []
    sede_ga = [Garantia.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []
    base_nc = [NoConformidad.empresa_id == p.ctx.empresa_id, *sede_nc]
    base_ga = [Garantia.empresa_id == p.ctx.empresa_id, *sede_ga]
    if p.producto_ids:
        base_nc.append(NoConformidad.producto_id.in_(p.producto_ids))
        base_ga.append(Garantia.producto_id.in_(p.producto_ids))
    if re.search(r"\b(vencer|vencen|vencimiento|venciendo|caducar|expirar)\b", f) and re.search(r"\bgarantia", f):
        limite = p.hoy + timedelta(days=30)
        filas = (await p.db.execute(
            select(Garantia, Producto.codigo, Producto.nombre, Sede.nombre.label("sede")).join(Producto, Producto.id == Garantia.producto_id).join(Sede, Sede.id == Garantia.sede_id)
            .where(*base_ga, Garantia.estado.in_(_ABIERTA_GARANTIA + ("aprobada",)), Garantia.garantia_hasta >= p.hoy, Garantia.garantia_hasta <= limite).order_by(Garantia.garantia_hasta)
        )).all()
        if not filas:
            return B.Resp(f"Ninguna garantía abierta {p.en_alcance} vence en los próximos 30 días.", enlaces=enlaces_a(p, "/sig/calidad"), sugerencias=["¿Qué garantías están abiertas?"])
        tabla = B.tabla(None, [B.col("n", "N.º"), B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("estado", "Estado"), B.col("hasta", "Vence", "fecha")],
                        [B.fila({"n": f"N.º {x.Garantia.numero}", "producto": nombre_producto(x.codigo, x.nombre), "sede": x.sede, "estado": B.ESTADO_GARANTIA.get(x.Garantia.estado, x.Garantia.estado), "hasta": x.Garantia.garantia_hasta},
                                ruta="/sig/calidad") for x in filas[: p.limite(10)]], total=len(filas), nota=nota_listado(min(len(filas), p.limite(10)), len(filas), "garantías"))
        return B.Resp(f"**{B.n_de(len(filas), 'garantía')}** {'vence' if len(filas) == 1 else 'vencen'} en los próximos 30 días {p.en_alcance}.", [tabla], enlaces_a(p, "/sig/calidad"), ["Resumen de calidad"])
    if re.search(r"\b(tiempo|tarda\w*|demor\w+|cuanto)\b", f) and re.search(r"\b(resol\w+|solucion\w+|cerr\w+|atend\w+)\b", f):
        nc = (await p.db.execute(select(NoConformidad.created_at, NoConformidad.resuelta_en).where(*base_nc, NoConformidad.resuelta_en.is_not(None)))).all()
        ga = (await p.db.execute(select(Garantia.fecha_reporte, Garantia.fecha_solucion).where(*base_ga, Garantia.fecha_solucion.is_not(None)))).all()
        partes, metricas = [], []
        if nc:
            prom = sum(_dias(a, b) for a, b in nc) / len(nc)
            partes.append(f"las no conformidades tardan **{_duracion(prom)}** ({B.n_de(len(nc), 'resuelta')})")
            metricas.append(("No conformidades", _duracion(prom), f"{B.n_de(len(nc), 'resuelta')}"))
        if ga:
            prom = sum((b - a).days for a, b in ga) / len(ga)
            partes.append(f"las garantías tardan **{B.decimal(prom, 1)} días** ({B.n_de(len(ga), 'solucionada')})")
            metricas.append(("Garantías", f"{B.decimal(prom, 1)} días", f"{B.n_de(len(ga), 'solucionada')}"))
        if not partes:
            return B.Resp(f"Todavía no hay no conformidades ni garantías resueltas {p.en_alcance} para medir tiempos.", enlaces=enlaces_a(p, "/sig/calidad"))
        return B.Resp(f"En promedio, {' y '.join(partes)} en resolverse {p.en_alcance}.", [B.metricas(None, *metricas)], enlaces_a(p, "/sig/calidad"), ["Resumen de calidad", "Proveedor con más problemas"])
    if re.search(r"\bproveedor\w*\b", f):
        cuenta: Counter[str] = Counter()
        for proveedor, n in (await p.db.execute(select(NoConformidad.proveedor, func.count()).where(*base_nc, NoConformidad.proveedor.is_not(None)).group_by(NoConformidad.proveedor))).all():
            cuenta[proveedor.strip()] += int(n)
        nc_por = dict(cuenta)
        gcuenta: Counter[str] = Counter()
        for proveedor, n in (await p.db.execute(select(Garantia.proveedor, func.count()).where(*base_ga, Garantia.proveedor.is_not(None)).group_by(Garantia.proveedor))).all():
            gcuenta[proveedor.strip()] += int(n)
        nombres = sorted(set(nc_por) | set(gcuenta), key=lambda n: -(nc_por.get(n, 0) + gcuenta.get(n, 0)))
        if not nombres:
            return B.Resp(f"Ninguna no conformidad ni garantía {p.en_alcance} tiene proveedor registrado, así que no puedo compararlos.", enlaces=enlaces_a(p, "/sig/calidad"))
        top = nombres[0]
        texto = f"El proveedor con más problemas {p.en_alcance} es **{top}**: {B.n_de(nc_por.get(top, 0), 'no conformidad', 'no conformidades')} y {B.n_de(gcuenta.get(top, 0), 'garantía')}."
        tabla = B.tabla(None, [B.col("proveedor", "Proveedor"), B.col("nc", "No conformidades", "entero"), B.col("ga", "Garantías", "entero"), B.col("t", "Total", "entero")],
                        [B.fila({"proveedor": n, "nc": nc_por.get(n, 0), "ga": gcuenta.get(n, 0), "t": nc_por.get(n, 0) + gcuenta.get(n, 0)}, ruta="/sig/calidad") for n in nombres[: p.limite(8)]], total=len(nombres))
        return B.Resp(texto, [tabla], enlaces_a(p, "/sig/calidad"), ["Resumen de calidad", "¿Qué garantías están abiertas?"], ["Solo cuentan los casos que tienen el proveedor registrado."])
    if re.search(r"\bproductos?\b", f) and not p.hay_producto:
        filas = (await p.db.execute(
            select(Producto.codigo, Producto.nombre, func.count().label("n"), func.coalesce(func.sum(NoConformidad.cantidad_afectada), 0).label("u")).select_from(NoConformidad)
            .join(Producto, Producto.id == NoConformidad.producto_id).where(*base_nc).group_by(Producto.codigo, Producto.nombre).order_by(func.count().desc(), Producto.nombre).limit(p.limite(8))
        )).all()
        garantias = (await p.db.execute(
            select(Producto.codigo, Producto.nombre, func.count().label("n")).select_from(Garantia).join(Producto, Producto.id == Garantia.producto_id).where(*base_ga)
            .group_by(Producto.codigo, Producto.nombre).order_by(func.count().desc(), Producto.nombre).limit(p.limite(8))
        )).all()
        if not filas and not garantias:
            return B.Resp(f"No hay no conformidades ni garantías {p.en_alcance} para comparar productos.", enlaces=enlaces_a(p, "/sig/calidad"))
        partes = []
        bloques = []
        if filas:
            partes.append(f"más no conformidades: **{nombre_producto(filas[0].codigo, filas[0].nombre)}** ({B.n_de(int(filas[0].n), 'caso')})")
            bloques.append(B.tabla("No conformidades por producto", [B.col("producto", "Producto"), B.col("n", "Casos", "entero"), B.col("u", "Unidades afectadas", "entero")],
                                   [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "n": int(x.n), "u": int(x.u)}, ruta="/sig/calidad") for x in filas]))
        if garantias:
            partes.append(f"más garantías: **{nombre_producto(garantias[0].codigo, garantias[0].nombre)}** ({B.n_de(int(garantias[0].n), 'caso')})")
            bloques.append(B.tabla("Garantías por producto", [B.col("producto", "Producto"), B.col("n", "Casos", "entero")],
                                   [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "n": int(x.n)}, ruta="/sig/calidad") for x in garantias]))
        return B.Resp(f"{B.mayuscula_inicial('; '.join(partes))} {p.en_alcance}.", bloques, enlaces_a(p, "/sig/calidad"), ["Resumen de calidad", "Proveedor con más problemas"])
    if re.search(r"\bsede\w*\b", f) and (p.sede_ids is None or len(p.sede_ids) > 1):
        filas = (await p.db.execute(select(Sede.nombre, func.count().label("n")).select_from(NoConformidad).join(Sede, Sede.id == NoConformidad.sede_id).where(*base_nc).group_by(Sede.nombre).order_by(func.count().desc()))).all()
        if filas:
            return B.Resp(f"La sede con más no conformidades es **{filas[0].nombre}** ({B.n_de(int(filas[0].n), 'caso')}).", [B.barras("No conformidades por sede", [(x.nombre, float(x.n), B.entero(x.n)) for x in filas])],
                          enlaces_a(p, "/sig/calidad"), ["Resumen de calidad"])
    tipos = (await p.db.execute(select(NoConformidad.tipo, func.count()).where(*base_nc).group_by(NoConformidad.tipo).order_by(func.count().desc()))).all()
    if not tipos:
        return B.Resp(f"No hay no conformidades registradas {p.en_alcance}.", enlaces=enlaces_a(p, "/sig/calidad"), sugerencias=["¿Qué garantías están abiertas?"])
    return B.Resp(f"El tipo de defecto más común {p.en_alcance} es **{B.TIPO_NC.get(tipos[0][0], tipos[0][0]).lower()}** ({B.n_de(int(tipos[0][1]), 'caso')}).",
                  [B.barras("No conformidades por tipo", [(B.TIPO_NC.get(t, t), float(n), B.entero(n)) for t, n in tipos])], enlaces_a(p, "/sig/calidad"), ["Proveedor con más problemas", "Producto con más no conformidades"])


# ================================================================================================== análisis de PQRS
@manejador("pqrs_analisis")
async def pqrs_analisis(p: Peticion) -> B.Resp:
    gestiona = p.tiene("pqrs.gestionar")
    cond = [Pqrs.empresa_id == p.ctx.empresa_id]
    if not gestiona:
        cond.append(Pqrs.usuario_id == p.ctx.usuario_id)
    elif p.sede_ids is not None:
        cond.append(Pqrs.sede_id.in_(p.sede_ids))
    quien = p.en_alcance if gestiona else "tuyas"
    f = p.frase
    if re.search(r"\b(tiempo|tarda\w*|demor\w+|cuanto)\b", f):
        filas = (await p.db.execute(select(Pqrs.created_at, Pqrs.respondida_en).where(*cond, Pqrs.respondida_en.is_not(None)))).all()
        if not filas:
            return B.Resp(f"Todavía no hay PQRS respondidas {quien} para medir el tiempo de respuesta.", enlaces=enlaces_a(p, "/sig/pqrs"))
        dias = sorted(_dias(a, b) for a, b in filas)
        return B.Resp(f"Las PQRS {quien} se responden en promedio en **{_duracion(sum(dias) / len(dias))}** (mediana {_duracion(dias[len(dias) // 2])}), sobre {B.n_de(len(dias), 'PQRS', 'PQRS')} respondidas.",
                      [B.metricas(None, ("Promedio", _duracion(sum(dias) / len(dias))), ("La más rápida", _duracion(dias[0])), ("La más lenta", _duracion(dias[-1])))], enlaces_a(p, "/sig/pqrs"), ["¿Cuántas PQRS hay pendientes?"])
    if re.search(r"\b(antigua\w*|viej\w+|sin responder|sin respuesta|sin atender|mas tiempo)\b", f):
        filas = (await p.db.execute(select(Pqrs).where(*cond, Pqrs.estado.in_(("pendiente", "en_revision", "en_proceso"))).order_by(Pqrs.created_at.asc()).limit(p.limite(8)))).scalars().all()
        if not filas:
            return B.Resp(f"No hay PQRS sin resolver {quien}.", enlaces=enlaces_a(p, "/sig/pqrs"))
        hoy_utc = inicio_de_dia_utc(p.hoy + timedelta(days=1))
        tabla = B.tabla(None, [B.col("n", "N.º"), B.col("tipo", "Tipo"), B.col("asunto", "Asunto"), B.col("estado", "Estado"), B.col("dias", "Días abierta", "entero")],
                        [B.fila({"n": f"N.º {x.numero}", "tipo": B.TIPO_PQRS.get(x.tipo, x.tipo), "asunto": x.asunto, "estado": B.ESTADO_PQRS.get(x.estado, (x.estado,))[0], "dias": max(0, int(_dias(x.created_at, hoy_utc)))},
                                tonos={"estado": B.ESTADO_PQRS.get(x.estado, ("", "neutral"))[1]}, ruta="/sig/pqrs") for x in filas])
        return B.Resp(f"La PQRS sin resolver más antigua {quien} es la **N.º {filas[0].numero}** («{filas[0].asunto}»), abierta hace {B.n_de(max(0, int(_dias(filas[0].created_at, hoy_utc))), 'día')}.", [tabla], enlaces_a(p, "/sig/pqrs"), ["¿Cuántas PQRS hay pendientes?"])
    por_tipo = (await p.db.execute(select(Pqrs.tipo, func.count()).where(*cond).group_by(Pqrs.tipo).order_by(func.count().desc()))).all()
    if not por_tipo:
        return B.Resp(f"No hay PQRS {quien}.", enlaces=enlaces_a(p, "/sig/pqrs"))
    bloques = [B.barras("Por tipo", [(B.TIPO_PQRS.get(t, t), float(n), B.entero(n)) for t, n in por_tipo])]
    texto = f"El tipo de PQRS más frecuente {quien} es **{B.TIPO_PQRS.get(por_tipo[0][0], por_tipo[0][0]).lower()}** ({B.n_de(int(por_tipo[0][1]), 'caso')})."
    if gestiona and (p.sede_ids is None or len(p.sede_ids) > 1):
        por_sede = (await p.db.execute(select(Sede.nombre, func.count()).select_from(Pqrs).join(Sede, Sede.id == Pqrs.sede_id).where(*cond).group_by(Sede.nombre).order_by(func.count().desc()))).all()
        if por_sede:
            bloques.append(B.barras("Por sede", [(n, float(c), B.entero(c)) for n, c in por_sede]))
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/pqrs"), ["PQRS más antiguas sin responder", "¿Cuánto tardan en responderse las PQRS?"])


# ====================================================================================== equivalencias ambientales
@manejador("ambiental_equivalencia")
async def ambiental_equivalencia(p: Peticion) -> B.Resp:
    periodo = p.periodo or L.Periodo(date(p.hoy.year, 1, 1), p.hoy, "este año")
    cond = [AmbRegistro.empresa_id == p.ctx.empresa_id, AmbRegistro.estado == "activo", AmbRegistro.fecha >= periodo.desde, AmbRegistro.fecha <= periodo.hasta]
    if p.sede_ids is not None:
        cond.append(AmbRegistro.sede_id.in_(p.sede_ids))
    f = (await p.db.execute(select(func.coalesce(func.sum(AmbRegistro.unidades), 0), func.coalesce(func.sum(AmbRegistro.co2_evitado_kg), 0)).where(*cond))).one()
    unidades, co2 = int(f[0]), float(f[1])
    if not co2:
        return B.Resp(f"Todavía no hay CO₂ evitado calculado {p.en_alcance} {p.en_periodo(periodo)}, así que no puedo hacer la equivalencia.", enlaces=enlaces_a(p, "/sig/ambiental"), sugerencias=["¿Cuánto CO₂ evitamos este año?"])
    arboles = co2 / KG_CO2_POR_ARBOL_AL_ANIO
    texto = (f"{p.periodo_inicio(periodo)} las {B.n_de(unidades, 'venta de vehículo eléctrico', 'ventas de vehículos eléctricos')} {p.en_alcance} evitaron cerca de **{B.entero(co2)} kg de CO₂**, "
             f"lo que equivale aproximadamente a lo que absorben **{B.entero(arboles)} árboles adultos en un año**.")
    return B.Resp(texto, [B.metricas(None, ("CO₂ evitado", f"{B.entero(co2)} kg"), ("Árboles equivalentes (1 año)", B.entero(arboles)), ("Vehículos vendidos", B.entero(unidades)))], enlaces_a(p, "/sig/ambiental"), ["¿Cuánto CO₂ evitamos este año?"],
                  [f"La equivalencia usa una referencia común de ≈{KG_CO2_POR_ARBOL_AL_ANIO} kg de CO₂ por árbol al año; es solo una forma de dimensionar la cifra, no un dato de tu empresa. El CO₂ evitado es una estimación."])


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
    (r"\bgestionar\b.*\bpqrs|\bresponder\b.*\bpqrs|\bpqrs\b.*\b(gestionar|responder)", "pqrs.gestionar", "gestionar y responder PQRS"),
    (r"\b(crear|enviar|radicar|hacer)\b.*\b(pqrs|queja|reclamo|peticion)", "pqrs.crear", "enviar PQRS"),
    (r"\breportar\b.*\b(no ?conformidad|garantia|calidad)|\b(no ?conformidad|garantia)\b.*\breportar", "calidad.reportar", "reportar no conformidades y garantías"),
    (r"\bgestionar\b.*\b(no ?conformidad|garantia|calidad)", "calidad.gestionar", "gestionar calidad (no conformidades y garantías)"),
    (r"\bsst\b.*\bgestionar|\bgestionar\b.*\b(sst|pausas)", "sst.gestionar", "gestionar Seguridad y Salud en el Trabajo"),
    (r"\bconfigurar\b.*\bambiental|\bambiental\b.*\bconfigurar", "ambiental.configurar", "configurar la gestión ambiental"),
    (r"\bagentes?\b|\bllaves?\b|\bintegraci\w+", "agentes.gestionar", "gestionar agentes de IA y llaves de acceso"),
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
