"""Seguridad y Salud en el Trabajo: pausas activas automáticas.

Cómo se evita mostrar pausas repetidas o simultáneas:
 * El SERVIDOR decide: ``iniciar_pausa`` solo crea una pausa si pasó el intervalo desde la última mostrada.
 * Una persona nunca tiene dos pausas abiertas: un índice único parcial lo garantiza en la base de datos
   (dos pestañas o dos peticiones simultáneas reciben LA MISMA pausa, no dos).
 * Recargar la página no genera otra: si hay una pausa abierta reciente se devuelve esa misma.
 * Una pausa abierta que nadie cerró se da por «omitida» pasado un tiempo, para no bloquear la siguiente.
Quien tenga ``sst.gestionar`` (administración) NO recibe pausas automáticas, pero puede ver todo el contenido."""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import NoEncontrado
from app.core.sql import bloqueo_asesor, insertar
from app.core.tiempo import ahora_utc, asegurar_utc, fin_de_dia_utc, hoy_local, inicio_de_dia_utc
from app.models.sst import SstActividad, SstConfiguracion, SstPausa
from app.schemas.comunes import ParametrosPagina
from app.schemas.sst import (
    ActividadActualizar,
    ActividadCrear,
    ActividadSalida,
    ConfiguracionSst,
    ConfiguracionSstActualizar,
    PausaCerrar,
    PausaEstado,
    PausaIniciada,
    PausaMostrada,
    PausaRegistro,
    ResumenSst,
    ResumenUsuarioSst,
)
from app.services import auditoria_service
from app.services.sig_util import nombres_usuarios

INTERVALO_POR_DEFECTO = 60  # minutos: práctica común de pausas activas durante la jornada
EXPIRA_PAUSA_ABIERTA = timedelta(minutes=30)
TOLERANCIA_INTERVALO = 0.9  # el servidor admite una pausa nueva desde el 90 % del intervalo (relojes distintos)

# Contenido inicial (editable por la administración). Un paso o consejo por línea.
ACTIVIDADES_INICIALES: tuple[dict, ...] = (
    {
        "titulo": "Estiramiento de cuello", "area": "cuello", "duracion_segundos": 60, "orden": 1,
        "mensaje": "Libera la tensión de la nuca y los hombros después de estar frente a la pantalla.",
        "instrucciones": (
            "Siéntate con la espalda recta y los hombros relajados.\n"
            "Inclina suavemente la cabeza hacia el hombro derecho y mantén 10 segundos.\n"
            "Vuelve al centro y repite hacia el lado izquierdo.\n"
            "Lleva el mentón hacia el pecho sin forzar y mantén 10 segundos.\n"
            "Repite la secuencia dos veces. No hagas giros bruscos ni lleves la cabeza hacia atrás."
        ),
        "recomendaciones": (
            "Ubica la parte superior de la pantalla a la altura de los ojos para no flexionar el cuello.\n"
            "Evita sostener el teléfono entre el hombro y la oreja."
        ),
    },
    {
        "titulo": "Círculos de hombros", "area": "hombros", "duracion_segundos": 45, "orden": 2,
        "mensaje": "Suelta los hombros: la tensión acumulada se nota al final del día.",
        "instrucciones": (
            "Ponte de pie o siéntate con la espalda recta.\n"
            "Sube los hombros hacia las orejas y mantén 3 segundos.\n"
            "Haz diez círculos lentos hacia atrás.\n"
            "Haz diez círculos lentos hacia adelante.\n"
            "Deja caer los brazos y respira profundo."
        ),
        "recomendaciones": "Mantén los codos cerca del cuerpo y apoya los antebrazos al escribir; evita encoger los hombros.",
    },
    {
        "titulo": "Estiramiento de muñecas y manos", "area": "manos_munecas", "duracion_segundos": 60, "orden": 3,
        "mensaje": "Cuida tus manos: teclear y usar el ratón durante horas las cansa.",
        "instrucciones": (
            "Extiende el brazo derecho al frente con la palma hacia arriba.\n"
            "Con la mano izquierda lleva suavemente los dedos hacia abajo y mantén 10 segundos.\n"
            "Gira la palma hacia abajo y llévala hacia ti con suavidad otros 10 segundos.\n"
            "Cambia de brazo y repite.\n"
            "Cierra y abre los puños diez veces, y sacude las manos con suavidad."
        ),
        "recomendaciones": (
            "Mantén las muñecas rectas, sin doblarlas hacia arriba ni hacia los lados, al teclear.\n"
            "Usa el ratón con el antebrazo apoyado y no lo aprietes."
        ),
    },
    {
        "titulo": "Descanso visual 20-20-20", "area": "ojos", "duracion_segundos": 60, "orden": 4,
        "mensaje": "Tus ojos también se cansan: dales un descanso lejos de la pantalla.",
        "instrucciones": (
            "Aparta la vista de la pantalla.\n"
            "Mira un objeto lejano (a unos 6 metros o más) durante 20 segundos.\n"
            "Parpadea varias veces, de forma completa y lenta, para humedecer los ojos.\n"
            "Frota las palmas para calentarlas y apóyalas unos segundos sobre los párpados cerrados."
        ),
        "recomendaciones": (
            "Regla 20-20-20: cada 20 minutos, mira algo lejano durante 20 segundos.\n"
            "Ajusta el brillo de la pantalla al de la sala y evita reflejos de ventanas."
        ),
    },
    {
        "titulo": "Estiramiento de espalda sentado", "area": "espalda", "duracion_segundos": 60, "orden": 5,
        "mensaje": "Alivia la zona lumbar y dorsal sin levantarte del puesto.",
        "instrucciones": (
            "Siéntate al borde de la silla con los pies apoyados en el piso.\n"
            "Entrelaza las manos, estira los brazos al frente y redondea suavemente la espalda 10 segundos.\n"
            "Lleva las manos detrás de la cabeza, abre los codos y estira el pecho 10 segundos.\n"
            "Gira el tronco con suavidad hacia un lado y hacia el otro, 10 segundos cada uno."
        ),
        "recomendaciones": (
            "Siéntate con la espalda apoyada en el respaldo, los pies en el piso y las rodillas a unos 90 grados.\n"
            "Cambia de postura con frecuencia; la mejor postura es la que se alterna."
        ),
    },
    {
        "titulo": "Activación de piernas y circulación", "area": "piernas", "duracion_segundos": 90, "orden": 6,
        "mensaje": "Levántate y mueve el cuerpo: la circulación mejora cuando caminas.",
        "instrucciones": (
            "Ponte de pie y camina durante 30 segundos.\n"
            "Apóyate en la silla o en la pared y sube a las puntas de los pies diez veces.\n"
            "Apoya los talones y levanta las puntas diez veces.\n"
            "Estira un poco las pantorrillas, una pierna atrás y la otra adelante, 10 segundos por lado."
        ),
        "recomendaciones": "Si pasas mucho tiempo sentado, levántate al menos una vez por hora, aunque sea para tomar agua.",
    },
    {
        "titulo": "Respiración consciente", "area": "respiracion", "duracion_segundos": 60, "orden": 7,
        "mensaje": "Un minuto de respiración tranquila ayuda a recuperar la atención.",
        "instrucciones": (
            "Siéntate cómodo, con la espalda recta y los hombros sueltos.\n"
            "Inhala por la nariz contando hasta 4.\n"
            "Sostén el aire contando hasta 4.\n"
            "Exhala lentamente por la boca contando hasta 6.\n"
            "Repite cinco veces."
        ),
        "recomendaciones": "Respira llevando el aire al abdomen y no solo al pecho; si te mareas, vuelve a respirar con normalidad.",
    },
)


# --------------------------------------------------------------------------- configuración y actividades


async def asegurar_configuracion(db: AsyncSession, empresa_id: int) -> SstConfiguracion:
    """Devuelve la configuración de la empresa; la primera vez la crea con valores razonables y el contenido inicial."""
    cfg = await db.get(SstConfiguracion, empresa_id)
    if cfg is not None:
        return cfg
    res = await db.execute(
        insertar(db, SstConfiguracion)
        .values(empresa_id=empresa_id, pausas_activas=True, intervalo_minutos=INTERVALO_POR_DEFECTO)
        .on_conflict_do_nothing(index_elements=["empresa_id"])
    )
    if res.rowcount == 1:  # solo quien la crea siembra el contenido (dos peticiones simultáneas no lo duplican)
        for datos in ACTIVIDADES_INICIALES:
            db.add(SstActividad(empresa_id=empresa_id, activa=True, **datos))
    await db.commit()
    return await db.scalar(
        select(SstConfiguracion).where(SstConfiguracion.empresa_id == empresa_id).execution_options(populate_existing=True)
    )


def _salida_config(cfg: SstConfiguracion) -> ConfiguracionSst:
    return ConfiguracionSst(pausas_activas=cfg.pausas_activas, intervalo_minutos=cfg.intervalo_minutos)


async def obtener_configuracion(db: AsyncSession, ctx: Contexto) -> ConfiguracionSst:
    return _salida_config(await asegurar_configuracion(db, ctx.empresa_id))


async def actualizar_configuracion(db: AsyncSession, ctx: Contexto, datos: ConfiguracionSstActualizar) -> ConfiguracionSst:
    ctx.exigir("sst.gestionar")
    cfg = await asegurar_configuracion(db, ctx.empresa_id)
    antes = {"pausas_activas": cfg.pausas_activas, "intervalo_minutos": cfg.intervalo_minutos}
    if datos.pausas_activas is not None:
        cfg.pausas_activas = datos.pausas_activas
    if datos.intervalo_minutos is not None:
        cfg.intervalo_minutos = datos.intervalo_minutos
    cfg.actualizado_por = ctx.usuario_id
    await auditoria_service.registrar(
        db, modulo="sst", accion="configurar", ctx=ctx, entidad="sst_configuracion", entidad_id=ctx.empresa_id,
        detalle={"antes": antes, "despues": {"pausas_activas": cfg.pausas_activas, "intervalo_minutos": cfg.intervalo_minutos}},
    )
    await db.commit()
    await db.refresh(cfg)
    return _salida_config(cfg)


async def listar_actividades(db: AsyncSession, ctx: Contexto, *, incluir_inactivas: bool) -> list[ActividadSalida]:
    await asegurar_configuracion(db, ctx.empresa_id)
    consulta = select(SstActividad).where(SstActividad.empresa_id == ctx.empresa_id)
    if not (incluir_inactivas and ctx.tiene("sst.gestionar")):
        consulta = consulta.where(SstActividad.activa.is_(True))
    filas = (await db.scalars(consulta.order_by(SstActividad.orden, SstActividad.id))).all()
    return [ActividadSalida.model_validate(a) for a in filas]


async def _actividad(db: AsyncSession, ctx: Contexto, actividad_id: int) -> SstActividad:
    a = await db.scalar(select(SstActividad).where(SstActividad.id == actividad_id, SstActividad.empresa_id == ctx.empresa_id))
    if a is None:
        raise NoEncontrado("La actividad no existe")
    return a


async def crear_actividad(db: AsyncSession, ctx: Contexto, datos: ActividadCrear) -> ActividadSalida:
    ctx.exigir("sst.gestionar")
    await asegurar_configuracion(db, ctx.empresa_id)
    a = SstActividad(empresa_id=ctx.empresa_id, **datos.model_dump())
    db.add(a)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="sst", accion="crear_actividad", ctx=ctx, entidad="sst_actividad", entidad_id=a.id, detalle={"titulo": a.titulo}
    )
    await db.commit()
    await db.refresh(a)
    return ActividadSalida.model_validate(a)


async def actualizar_actividad(db: AsyncSession, ctx: Contexto, actividad_id: int, datos: ActividadActualizar) -> ActividadSalida:
    ctx.exigir("sst.gestionar")
    a = await _actividad(db, ctx, actividad_id)
    for campo in datos.model_fields_set:
        valor = getattr(datos, campo)
        if valor is None and campo not in ("recomendaciones",):
            continue  # los campos obligatorios no se pueden vaciar
        setattr(a, campo, valor)
    await auditoria_service.registrar(
        db, modulo="sst", accion="editar_actividad", ctx=ctx, entidad="sst_actividad", entidad_id=a.id,
        detalle={"titulo": a.titulo, "campos": sorted(datos.model_fields_set)},
    )
    await db.commit()
    await db.refresh(a)
    return ActividadSalida.model_validate(a)


async def eliminar_actividad(db: AsyncSession, ctx: Contexto, actividad_id: int) -> None:
    """Elimina la actividad; el historial de pausas conserva su título (la referencia queda en nulo)."""
    ctx.exigir("sst.gestionar")
    a = await _actividad(db, ctx, actividad_id)
    await auditoria_service.registrar(
        db, modulo="sst", accion="eliminar_actividad", ctx=ctx, entidad="sst_actividad", entidad_id=a.id, detalle={"titulo": a.titulo}
    )
    await db.delete(a)
    await db.commit()


# --------------------------------------------------------------------------- pausas automáticas


def aplica_pausas(ctx: Contexto) -> bool:
    """Las pausas automáticas son para el personal operativo; quien administra el SST queda excluido."""
    return not ctx.tiene("sst.gestionar")


def _mostrada(p: SstPausa, actividades: dict[int, SstActividad]) -> PausaMostrada:
    a = actividades.get(p.actividad_id) if p.actividad_id else None
    return PausaMostrada(id=p.id, mostrada_en=p.mostrada_en, actividad=ActividadSalida.model_validate(a) if a else None)


async def _cargar_actividad(db: AsyncSession, actividad_id: int | None) -> dict[int, SstActividad]:
    if not actividad_id:
        return {}
    a = await db.get(SstActividad, actividad_id)
    return {a.id: a} if a else {}


async def _pausa_abierta(db: AsyncSession, ctx: Contexto) -> SstPausa | None:
    """Pausa «mostrada» sin cerrar. Si lleva demasiado tiempo abierta se da por omitida y se devuelve ``None``."""
    pausa = await db.scalar(
        select(SstPausa).where(SstPausa.usuario_id == ctx.usuario_id, SstPausa.estado == "mostrada")
        .execution_options(populate_existing=True)
    )
    if pausa is None:
        return None
    ahora = ahora_utc()
    if ahora - asegurar_utc(pausa.mostrada_en) > EXPIRA_PAUSA_ABIERTA:
        await db.execute(
            update(SstPausa).where(SstPausa.id == pausa.id, SstPausa.estado == "mostrada").values(estado="omitida", cerrada_en=ahora)
        )
        await db.commit()
        return None
    return pausa


async def _ultima_mostrada(db: AsyncSession, ctx: Contexto) -> datetime | None:
    ultima = await db.scalar(select(func.max(SstPausa.mostrada_en)).where(SstPausa.usuario_id == ctx.usuario_id))
    return asegurar_utc(ultima) if ultima else None


async def estado_pausas(db: AsyncSession, ctx: Contexto) -> PausaEstado:
    cfg = await asegurar_configuracion(db, ctx.empresa_id)
    aplica = aplica_pausas(ctx)
    pendiente = await _pausa_abierta(db, ctx) if aplica else None
    return PausaEstado(
        aplica=aplica, activo=cfg.pausas_activas, intervalo_minutos=cfg.intervalo_minutos, ahora=ahora_utc(),
        ultima_pausa_en=await _ultima_mostrada(db, ctx),
        pendiente=_mostrada(pendiente, await _cargar_actividad(db, pendiente.actividad_id)) if pendiente else None,
    )


async def iniciar_pausa(db: AsyncSession, ctx: Contexto) -> PausaIniciada:
    """Pide al servidor mostrar una pausa. Responde ``mostrar=False`` si no corresponde (todavía)."""
    if not aplica_pausas(ctx):
        return PausaIniciada(mostrar=False, motivo="excluido")
    cfg = await asegurar_configuracion(db, ctx.empresa_id)
    if not cfg.pausas_activas:
        return PausaIniciada(mostrar=False, motivo="desactivadas")

    await bloqueo_asesor(db, 7_100_000_000 + ctx.usuario_id)  # serializa a la misma persona (PostgreSQL)
    abierta = await _pausa_abierta(db, ctx)
    if abierta is not None:
        return PausaIniciada(mostrar=True, pausa=_mostrada(abierta, await _cargar_actividad(db, abierta.actividad_id)))

    ahora = ahora_utc()
    intervalo = timedelta(minutes=cfg.intervalo_minutos)
    ultima = await _ultima_mostrada(db, ctx)
    if ultima is not None and ahora - ultima < intervalo * TOLERANCIA_INTERVALO:
        return PausaIniciada(mostrar=False, motivo="muy_pronto", proxima_en=ultima + intervalo)

    actividades = (
        await db.scalars(
            select(SstActividad).where(SstActividad.empresa_id == ctx.empresa_id, SstActividad.activa.is_(True))
            .order_by(SstActividad.orden, SstActividad.id)
        )
    ).all()
    if not actividades:
        return PausaIniciada(mostrar=False, motivo="sin_actividades")
    # Rota: primero la actividad que esta persona vio hace más tiempo (o nunca).
    vistas = dict(
        (await db.execute(
            select(SstPausa.actividad_id, func.max(SstPausa.mostrada_en)).where(SstPausa.usuario_id == ctx.usuario_id)
            .group_by(SstPausa.actividad_id)
        )).all()
    )
    minimo = datetime.min.replace(tzinfo=ahora.tzinfo)
    elegida = min(actividades, key=lambda a: (asegurar_utc(vistas[a.id]) if vistas.get(a.id) else minimo, a.orden, a.id))

    pausa = SstPausa(
        empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, actividad_id=elegida.id, actividad_titulo=elegida.titulo,
        mostrada_en=ahora, estado="mostrada",
    )
    db.add(pausa)
    try:
        await db.commit()
    except IntegrityError:  # otra pestaña la abrió en el mismo instante: se devuelve esa misma pausa
        await db.rollback()
        existente = await _pausa_abierta(db, ctx)
        if existente is None:
            return PausaIniciada(mostrar=False, motivo="muy_pronto", proxima_en=ahora + intervalo)
        return PausaIniciada(mostrar=True, pausa=_mostrada(existente, await _cargar_actividad(db, existente.actividad_id)))
    return PausaIniciada(mostrar=True, pausa=_mostrada(pausa, {elegida.id: elegida}))


async def cerrar_pausa(db: AsyncSession, ctx: Contexto, pausa_id: int, datos: PausaCerrar) -> PausaRegistro:
    """Marca la pausa como realizada u omitida. Es idempotente: cerrar dos veces no cambia el primer resultado."""
    pausa = await db.scalar(
        select(SstPausa).where(SstPausa.id == pausa_id, SstPausa.usuario_id == ctx.usuario_id, SstPausa.empresa_id == ctx.empresa_id)
    )
    if pausa is None:
        raise NoEncontrado("La pausa no existe")
    await db.execute(
        update(SstPausa).where(SstPausa.id == pausa.id, SstPausa.estado == "mostrada")
        .values(estado=datos.resultado, cerrada_en=ahora_utc(), duracion_segundos=datos.duracion_segundos)
    )
    await db.commit()
    await db.refresh(pausa)
    return PausaRegistro(
        id=pausa.id, usuario_id=pausa.usuario_id, usuario_nombre=ctx.usuario.nombre, actividad_titulo=pausa.actividad_titulo,
        mostrada_en=pausa.mostrada_en, estado=pausa.estado, cerrada_en=pausa.cerrada_en, duracion_segundos=pausa.duracion_segundos,
    )


# --------------------------------------------------------------------------- registro y cumplimiento


async def listar_pausas(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, ambito: str, usuario_id: int | None, estado: str | None,
    desde: date | None, hasta: date | None,
) -> tuple[list[PausaRegistro], int]:
    condiciones = [SstPausa.empresa_id == ctx.empresa_id]
    if ambito == "todas":
        ctx.exigir("sst.gestionar")
        if usuario_id:
            condiciones.append(SstPausa.usuario_id == usuario_id)
    else:
        condiciones.append(SstPausa.usuario_id == ctx.usuario_id)
    if estado:
        condiciones.append(SstPausa.estado == estado)
    if desde:
        condiciones.append(SstPausa.mostrada_en >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(SstPausa.mostrada_en < fin_de_dia_utc(hasta))
    total = await db.scalar(select(func.count()).select_from(SstPausa).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(SstPausa).where(*condiciones).order_by(SstPausa.mostrada_en.desc(), SstPausa.id.desc())
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    nombres = await nombres_usuarios(db, {p.usuario_id for p in filas})
    return [
        PausaRegistro(
            id=p.id, usuario_id=p.usuario_id, usuario_nombre=nombres.get(p.usuario_id), actividad_titulo=p.actividad_titulo,
            mostrada_en=p.mostrada_en, estado=p.estado, cerrada_en=p.cerrada_en, duracion_segundos=p.duracion_segundos,
        )
        for p in filas
    ], total


async def resumen(db: AsyncSession, ctx: Contexto, dias: int) -> ResumenSst:
    ctx.exigir("sst.gestionar")
    desde = hoy_local() - timedelta(days=dias - 1)
    filas = (
        await db.execute(
            select(SstPausa.usuario_id, SstPausa.estado, func.count()).where(
                SstPausa.empresa_id == ctx.empresa_id, SstPausa.mostrada_en >= inicio_de_dia_utc(desde)
            ).group_by(SstPausa.usuario_id, SstPausa.estado)
        )
    ).all()
    por_usuario: dict[int, dict[str, int]] = {}
    for usuario_id, estado, cantidad in filas:
        por_usuario.setdefault(usuario_id, {"mostrada": 0, "realizada": 0, "omitida": 0})[estado] = int(cantidad)
    nombres = await nombres_usuarios(db, set(por_usuario))
    realizadas = sum(v["realizada"] for v in por_usuario.values())
    omitidas = sum(v["omitida"] for v in por_usuario.values())
    sin_responder = sum(v["mostrada"] for v in por_usuario.values())
    total = realizadas + omitidas + sin_responder
    return ResumenSst(
        desde=desde, mostradas=total, realizadas=realizadas, omitidas=omitidas, sin_responder=sin_responder,
        cumplimiento=round(100 * realizadas / total, 1) if total else None,
        por_usuario=sorted(
            (
                ResumenUsuarioSst(
                    usuario_id=u, usuario_nombre=nombres.get(u), mostradas=sum(v.values()), realizadas=v["realizada"],
                    omitidas=v["omitida"],
                )
                for u, v in por_usuario.items()
            ),
            key=lambda r: (-r.mostradas, r.usuario_nombre or ""),
        ),
    )
