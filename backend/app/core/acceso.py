"""Contexto de la persona autenticada: quién es, a qué empresa pertenece, qué permisos tiene y
a qué sedes puede acceder. Todos los servicios reciben este contexto en lugar de confiar en
identificadores enviados por el navegador (aislamiento multiempresa y multisede — RNF-024)."""

from dataclasses import dataclass

from app.core.exceptions import SinPermiso
from app.models.acceso import Rol
from app.models.usuario import Usuario


@dataclass(frozen=True)
class Contexto:
    usuario: Usuario
    permisos: frozenset[str]

    @property
    def empresa_id(self) -> int:
        return self.usuario.empresa_id

    @property
    def usuario_id(self) -> int:
        return self.usuario.id

    @property
    def rol(self) -> Rol:
        return self.usuario.rol

    @property
    def limitado_a_sede(self) -> bool:
        return self.rol.alcance == "sede"

    @property
    def sede_id(self) -> int | None:
        return self.usuario.sede_id

    def tiene(self, permiso: str) -> bool:
        return permiso in self.permisos

    def tiene_alguno(self, *permisos: str) -> bool:
        return any(p in self.permisos for p in permisos)

    def exigir(self, *permisos: str) -> None:
        """Lanza 403 si no tiene NINGUNO de los permisos indicados."""
        if not self.tiene_alguno(*permisos):
            raise SinPermiso("No tienes permiso para realizar esta acción")

    def sedes_autorizadas(self) -> list[int] | None:
        """``None`` = todas las sedes de la empresa; lista = solo esas."""
        if self.limitado_a_sede:
            return [self.sede_id] if self.sede_id is not None else []
        return None
