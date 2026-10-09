"""Acceso de agentes de IA (RNF-049): llaves de solo lectura con alcances explícitos.

 * La llave completa se muestra UNA sola vez al crearla; en base de datos solo se guarda su huella SHA-256.
 * Cada llave pertenece a una empresa, puede limitarse a una sede, caduca y se puede revocar.
 * Una llave solo puede consultar los recursos de sus alcances; todo lo demás recibe 403. Un agente
 *   NUNCA puede modificar datos. Los intentos con una llave inválida o sin alcance quedan en auditoría.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import NoAutenticado, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.niveles import clasificar_stock
from app.core.tiempo import ahora_utc, asegurar_utc
from app.models.auditoria import ApiKey
from app.models.catalogo import Producto
from app.models.enums import EstadoAlerta, EstadoRecomendacion
from app.models.inventario import Alerta, InventarioSede
from app.models.prediccion import Prediccion, Recomendacion
from app.models.sede import Sede
from app.schemas.comunes import ParametrosPagina
from app.schemas.prediccion import LlaveCrear, LlaveSalida
from app.services import auditoria_service, prediccion_service
from app.services.alcance import obtener_sede_de_empresa

ALCANCES = {
    "inventario:leer": "Consultar existencias por sede",
    "alertas:leer": "Consultar alertas de inventario activas",
    "predicciones:leer": "Consultar la última predicción de demanda",
    "recomendaciones:leer": "Consultar recomendaciones pendientes",
}
PREFIJO = "inv_"


@dataclass(frozen=True)
class ContextoAgente:
    llave_id: int
    nombre: str
    empresa_id: int
    sede_id: int | None
    alcances: frozenset[str]

    def exigir(self, alcance: str) -> None:
        if alcance not in self.alcances:
            raise SinPermiso(f"Esta llave no tiene autorizado el alcance «{alcance}»", codigo="alcance_no_autorizado")

    def sede_permitida(self, sede_id: int | None) -> int | None:
        """Sede a consultar: una llave limitada a una sede nunca puede ver otra."""
        if self.sede_id is not None:
            if sede_id is not None and sede_id != self.sede_id:
                raise SinPermiso("Esta llave solo puede consultar su sede", codigo="sede_no_autorizada")
            return self.sede_id
        return sede_id


def _huella(llave: str) -> str:
    return hashlib.sha256(llave.encode()).hexdigest()


def _salida(k: ApiKey) -> LlaveSalida:
    return LlaveSalida(
        id=k.id, nombre=k.nombre, prefijo=k.prefijo, alcances=list(k.alcances or []), sede_id=k.sede_id, activa=k.activa,
        creada_en=k.creada_en, expira_en=k.expira_en, ultimo_uso_en=k.ultimo_uso_en,
    )


async def crear_llave(db: AsyncSession, ctx: Contexto, datos: LlaveCrear) -> tuple[ApiKey, str]:
    desconocidos = set(datos.alcances) - ALCANCES.keys()
    if desconocidos:
        raise ReglaNegocio(f"Alcances desconocidos: {', '.join(sorted(desconocidos))}", codigo="alcance_desconocido")
    if datos.sede_id is not None:
        await obtener_sede_de_empresa(db, ctx.empresa_id, datos.sede_id)
    while True:
        prefijo = PREFIJO + secrets.token_hex(4)
        if await db.scalar(select(ApiKey.id).where(ApiKey.prefijo == prefijo)) is None:
            break
    llave = f"{prefijo}_{secrets.token_urlsafe(32)}"
    k = ApiKey(
        empresa_id=ctx.empresa_id, sede_id=datos.sede_id, nombre=datos.nombre, prefijo=prefijo, key_hash=_huella(llave),
        alcances=sorted(set(datos.alcances)), activa=True, creada_por=ctx.usuario_id,
        expira_en=ahora_utc() + timedelta(days=datos.dias_vigencia) if datos.dias_vigencia else None,
    )
    db.add(k)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="agentes", accion="crear_llave", ctx=ctx, entidad="api_key", entidad_id=k.id,
        detalle={"nombre": k.nombre, "prefijo": k.prefijo, "alcances": k.alcances, "sede_id": k.sede_id,
                 "expira_en": k.expira_en},
    )
    await db.commit()
    await db.refresh(k)
    return k, llave


async def listar_llaves(db: AsyncSession, ctx: Contexto) -> list[LlaveSalida]:
    filas = await db.scalars(select(ApiKey).where(ApiKey.empresa_id == ctx.empresa_id).order_by(ApiKey.id.desc()))
    return [_salida(k) for k in filas.all()]


async def revocar_llave(db: AsyncSession, ctx: Contexto, llave_id: int) -> LlaveSalida:
    k = await db.scalar(select(ApiKey).where(ApiKey.id == llave_id, ApiKey.empresa_id == ctx.empresa_id))
    if k is None:
        raise NoEncontrado("La llave no existe")
    if k.activa:
        k.activa = False
        await auditoria_service.registrar(
            db, modulo="agentes", accion="revocar_llave", ctx=ctx, entidad="api_key", entidad_id=k.id,
            detalle={"nombre": k.nombre, "prefijo": k.prefijo},
        )
        await db.commit()
        await db.refresh(k)
    return _salida(k)


async def autenticar(db: AsyncSession, llave: str | None) -> ContextoAgente:
    """Valida la llave. Cualquier fallo responde igual (401) para no revelar si el prefijo existe."""
    rechazo = NoAutenticado("Llave de acceso no válida o vencida", codigo="llave_invalida")
    if not llave or not llave.startswith(PREFIJO) or len(llave) > 120:
        raise rechazo
    prefijo = llave[: len(PREFIJO) + 8]
    k = await db.scalar(select(ApiKey).where(ApiKey.prefijo == prefijo))
    if k is None or not hmac.compare_digest(k.key_hash, _huella(llave)):
        await auditoria_service.registrar_independiente(
            modulo="agentes", accion="acceso_rechazado", resultado="fallido", detalle={"prefijo": prefijo[:12]}
        )
        raise rechazo
    if not k.activa or (k.expira_en is not None and asegurar_utc(k.expira_en) <= ahora_utc()):
        await auditoria_service.registrar_independiente(
            modulo="agentes", accion="acceso_rechazado", empresa_id=k.empresa_id, entidad="api_key", entidad_id=k.id,
            resultado="fallido", detalle={"motivo": "revocada o vencida", "prefijo": k.prefijo},
        )
        raise rechazo
    k.ultimo_uso_en = ahora_utc()
    await db.commit()
    return ContextoAgente(
        llave_id=k.id, nombre=k.nombre, empresa_id=k.empresa_id, sede_id=k.sede_id, alcances=frozenset(k.alcances or [])
    )


async def registrar_denegacion(agente: ContextoAgente, recurso: str, motivo: str) -> None:
    await auditoria_service.registrar_independiente(
        modulo="agentes", accion="acceso_denegado", empresa_id=agente.empresa_id, entidad="api_key",
        entidad_id=agente.llave_id, resultado="fallido", detalle={"recurso": recurso, "motivo": motivo},
    )


# ------------------------------------------------------------------------------- consultas
async def inventario(db: AsyncSession, a: ContextoAgente, pag: ParametrosPagina, sede_id: int | None, q: str | None):
    sede_id = a.sede_permitida(sede_id)
    base = (
        select(InventarioSede, Producto, Sede)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .join(Sede, Sede.id == InventarioSede.sede_id)
        .where(InventarioSede.empresa_id == a.empresa_id)
    )
    if sede_id is not None:
        base = base.where(InventarioSede.sede_id == sede_id)
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(Sede.nombre, Producto.nombre).offset(pag.offset).limit(pag.tamano))).all()
    return [
        {"sede": s.nombre, "sede_id": s.id, "codigo": p.codigo, "producto": p.nombre, "unidad": p.unidad_medida,
         "cantidad": i.cantidad, "stock_minimo": i.stock_minimo, "stock_maximo": i.stock_maximo,
         "estado": clasificar_stock(i.cantidad, i.stock_minimo, i.stock_maximo)}
        for i, p, s in filas
    ], int(total)


async def alertas(db: AsyncSession, a: ContextoAgente, pag: ParametrosPagina, sede_id: int | None, tipo: str | None):
    sede_id = a.sede_permitida(sede_id)
    base = (
        select(Alerta, Producto, Sede)
        .join(Producto, Producto.id == Alerta.producto_id)
        .join(Sede, Sede.id == Alerta.sede_id)
        .where(Alerta.empresa_id == a.empresa_id, Alerta.estado == EstadoAlerta.ACTIVA)
    )
    if sede_id is not None:
        base = base.where(Alerta.sede_id == sede_id)
    if tipo:
        base = base.where(Alerta.tipo == tipo)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(Alerta.abierta_en.desc()).offset(pag.offset).limit(pag.tamano))).all()
    return [
        {"tipo": al.tipo, "prioridad": al.prioridad, "mensaje": al.mensaje, "sede": s.nombre, "codigo": p.codigo,
         "producto": p.nombre, "abierta_en": al.abierta_en.isoformat()}
        for al, p, s in filas
    ], int(total)


async def predicciones(db: AsyncSession, a: ContextoAgente, pag: ParametrosPagina, sede_id: int | None, q: str | None):
    sede_id = a.sede_permitida(sede_id)
    ejecucion = await prediccion_service.ultima_completada(db, a.empresa_id)
    if ejecucion is None:
        return [], 0, None
    base = (
        select(Prediccion, Producto, Sede)
        .join(Producto, Producto.id == Prediccion.producto_id)
        .join(Sede, Sede.id == Prediccion.sede_id)
        .where(Prediccion.ejecucion_id == ejecucion.id)
    )
    if sede_id is not None:
        base = base.where(Prediccion.sede_id == sede_id)
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(Sede.nombre, Producto.nombre).offset(pag.offset).limit(pag.tamano))).all()
    return [
        {"sede": s.nombre, "codigo": p.codigo, "producto": p.nombre, "desde": pr.fecha_inicio.isoformat(),
         "hasta": pr.fecha_fin.isoformat(), "demanda_estimada": float(pr.demanda_estimada),
         "limite_inferior": None if pr.limite_inferior is None else float(pr.limite_inferior),
         "limite_superior": None if pr.limite_superior is None else float(pr.limite_superior),
         "modelo": pr.modelo, "confianza": pr.confianza, "es_estimacion": True}
        for pr, p, s in filas
    ], int(total), ejecucion


async def recomendaciones(db: AsyncSession, a: ContextoAgente, pag: ParametrosPagina, sede_id: int | None):
    sede_id = a.sede_permitida(sede_id)
    base = (
        select(Recomendacion, Producto, Sede)
        .join(Producto, Producto.id == Recomendacion.producto_id)
        .join(Sede, Sede.id == Recomendacion.sede_id)
        .where(Recomendacion.empresa_id == a.empresa_id, Recomendacion.estado == EstadoRecomendacion.PENDIENTE)
    )
    if sede_id is not None:
        base = base.where(Recomendacion.sede_id == sede_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(Recomendacion.generada_en.desc()).offset(pag.offset).limit(pag.tamano))).all()
    return [
        {"tipo": r.tipo, "prioridad": r.prioridad, "sede": s.nombre, "codigo": p.codigo, "producto": p.nombre,
         "cantidad_sugerida": r.cantidad_sugerida, "resumen": r.resumen, "requiere_aprobacion_humana": True}
        for r, p, s in filas
    ], int(total)
