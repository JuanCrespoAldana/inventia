from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.empresa import EmpresaActualizar, EmpresaSalida, ParametrosEmpresa
from app.services import empresa_service

router = APIRouter(prefix="/api/empresa", tags=["Empresa"])


@router.get("", response_model=EmpresaSalida, summary="Consultar la empresa")
async def consultar(ctx: Contexto = Depends(requiere("empresa.ver", "empresa.editar")), db: AsyncSession = Depends(get_db)):
    return empresa_service.a_salida(await empresa_service.obtener(db, ctx))


@router.put("", response_model=EmpresaSalida, summary="Modificar los datos de la empresa")
async def modificar(
    datos: EmpresaActualizar, ctx: Contexto = Depends(requiere("empresa.editar")), db: AsyncSession = Depends(get_db)
):
    return empresa_service.a_salida(await empresa_service.actualizar(db, ctx, datos))


@router.put("/parametros", response_model=EmpresaSalida, summary="Configurar plazos y reglas de inventario/IA")
async def modificar_parametros(
    datos: ParametrosEmpresa, ctx: Contexto = Depends(requiere("empresa.editar")), db: AsyncSession = Depends(get_db)
):
    return empresa_service.a_salida(await empresa_service.actualizar_parametros(db, ctx, datos))
