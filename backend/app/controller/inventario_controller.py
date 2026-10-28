from datetime import date

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.dto.inventario_dto import (
    AjusteCrear,
    ConsolidadoFila,
    EntradaCrear,
    EntradaDetalle,
    EntradaObservacionCrear,
    EntradaResumen,
    InventarioFila,
    MovimientoSalida,
    NivelesActualizar,
    ResultadoOperacion,
    SalidaCrear,
)
from app.dto.sede_dto import SedeResumen
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import entradas_service
from app.service import inventario_service as svc
from app.util.niveles import ESTADOS_STOCK

router = APIRouter(prefix="/api", tags=["Inventario"])


class InventarioSedePagina(Pagina[InventarioFila]):
    sede: SedeResumen


async def _resultado(db: AsyncSession, mensaje: str, movs, alertas) -> ResultadoOperacion:
    salidas = await svc.movimientos_a_salidas(db, movs)
    primera = salidas[0] if salidas else None
    return ResultadoOperacion(
        mensaje=mensaje, movimientos=salidas, alertas_abiertas=alertas["abiertas"], alertas_resueltas=alertas["resueltas"],
        entrada_id=primera.entrada_id if primera else None, entrada_numero=primera.entrada_numero if primera else None,
    )


@router.get("/inventario", response_model=InventarioSedePagina, summary="Existencias de una sede")
async def inventario_por_sede(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0, description="Obligatoria salvo para usuarios de una sola sede"),
    q: str | None = Query(None, max_length=100),
    categoria_id: int | None = Query(None, gt=0),
    estado: str | None = Query(None, pattern="^(" + "|".join(ESTADOS_STOCK) + ")$"),
    ctx: Contexto = Depends(requiere("inventario.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total, sede = await svc.listar_inventario(db, ctx, pag, sede_id=sede_id, q=q, categoria_id=categoria_id, estado=estado)
    pagina = Pagina.crear(filas, total, pag.pagina, pag.tamano)
    return InventarioSedePagina(**pagina.model_dump(), sede=SedeResumen.model_validate(sede))


@router.get("/inventario/consolidado", response_model=Pagina[ConsolidadoFila], summary="Inventario consolidado de la empresa")
async def inventario_consolidado(
    pag: ParametrosPagina = Depends(),
    q: str | None = Query(None, max_length=100),
    categoria_id: int | None = Query(None, gt=0),
    solo_con_existencias: bool = Query(False),
    ctx: Contexto = Depends(requiere("inventario.consolidado")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.consolidado(db, ctx, pag, q=q, categoria_id=categoria_id, solo_con_existencias=solo_con_existencias)
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("/inventario/entradas", response_model=ResultadoOperacion, status_code=status.HTTP_201_CREATED,
             summary="Registrar entrada de productos")
async def entrada(datos: EntradaCrear, ctx: Contexto = Depends(requiere("inventario.entrada")), db: AsyncSession = Depends(get_db)):
    movs, alertas = await svc.registrar_entrada(db, ctx, datos)
    return await _resultado(db, "Entrada registrada", movs, alertas)


@router.get("/inventario/entradas", response_model=Pagina[EntradaResumen], summary="Entradas de mercancía registradas")
async def entradas(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    numero: int | None = Query(None, gt=0, description="Número de la entrada"),
    ctx: Contexto = Depends(requiere("movimientos.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await entradas_service.listar_entradas(db, ctx, pag, sede_id=sede_id, desde=desde, hasta=hasta, numero=numero)
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.get("/inventario/entradas/{entrada_id}", response_model=EntradaDetalle,
            summary="Detalle de una entrada con su historial de observaciones")
async def entrada_detalle(entrada_id: int, ctx: Contexto = Depends(requiere("movimientos.ver")), db: AsyncSession = Depends(get_db)):
    return await entradas_service.detalle(db, ctx, await entradas_service.obtener_entrada(db, ctx, entrada_id))


@router.post("/inventario/entradas/{entrada_id}/observaciones", response_model=EntradaDetalle,
             status_code=status.HTTP_201_CREATED, summary="Agregar una observación a una entrada")
async def entrada_observar(
    entrada_id: int, datos: EntradaObservacionCrear,
    ctx: Contexto = Depends(requiere("inventario.entrada")), db: AsyncSession = Depends(get_db),
):
    return await entradas_service.agregar_observacion(db, ctx, entrada_id, datos)


@router.post("/inventario/salidas", response_model=ResultadoOperacion, status_code=status.HTTP_201_CREATED,
             summary="Registrar salida de productos")
async def salida(datos: SalidaCrear, ctx: Contexto = Depends(requiere("inventario.salida")), db: AsyncSession = Depends(get_db)):
    movs, alertas = await svc.registrar_salida(db, ctx, datos)
    return await _resultado(db, "Salida registrada", movs, alertas)


@router.post("/inventario/ajustes", response_model=ResultadoOperacion, status_code=status.HTTP_201_CREATED,
             summary="Ajustar existencias a un conteo físico")
async def ajuste(datos: AjusteCrear, ctx: Contexto = Depends(requiere("inventario.ajustar")), db: AsyncSession = Depends(get_db)):
    movs, alertas = await svc.ajustar(db, ctx, datos)
    return await _resultado(db, "Ajuste registrado", movs, alertas)


class NivelesSalida(BaseModel):
    sede_id: int
    producto_id: int
    cantidad: int
    stock_minimo: int
    stock_maximo: int | None


@router.put("/inventario/niveles", response_model=NivelesSalida, summary="Configurar stock mínimo y máximo")
async def niveles(datos: NivelesActualizar, ctx: Contexto = Depends(requiere("inventario.niveles")), db: AsyncSession = Depends(get_db)):
    fila = await svc.configurar_niveles(db, ctx, datos)
    return NivelesSalida(
        sede_id=fila.sede_id, producto_id=fila.producto_id, cantidad=fila.cantidad,
        stock_minimo=fila.stock_minimo, stock_maximo=fila.stock_maximo,
    )


@router.get("/movimientos", response_model=Pagina[MovimientoSalida], summary="Historial de movimientos")
async def movimientos(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    producto_id: int | None = Query(None, gt=0),
    tipo: str | None = Query(None, max_length=30),
    usuario_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    ctx: Contexto = Depends(requiere("movimientos.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_movimientos(
        db, ctx, pag, sede_id=sede_id, producto_id=producto_id, tipo=tipo, desde=desde, hasta=hasta, usuario_id=usuario_id
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)
