"""Mapper de empresa: convierte la entidad Empresa en su DTO de salida."""

from app.dto.empresa_dto import EmpresaSalida
from app.model.empresa import Empresa


def a_empresa_salida(empresa: Empresa) -> EmpresaSalida:
    return EmpresaSalida(
        id=empresa.id, nombre=empresa.nombre, identificacion=empresa.identificacion, direccion=empresa.direccion,
        ciudad=empresa.ciudad, telefono=empresa.telefono, email=empresa.email, activa=empresa.activa,
        parametros=empresa.parametros(), created_at=empresa.created_at, updated_at=empresa.updated_at,
    )
