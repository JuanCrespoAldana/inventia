"""Valores controlados del dominio. En base de datos se guardan como texto (sin ENUM nativo)
para que añadir un valor nuevo no exija migrar tipos de PostgreSQL."""

from enum import StrEnum


class AlcanceRol(StrEnum):
    EMPRESA = "empresa"
    SEDE = "sede"


class TipoMovimiento(StrEnum):
    ENTRADA = "entrada"
    SALIDA = "salida"
    AJUSTE = "ajuste"
    VENTA = "venta"
    ANULACION_VENTA = "anulacion_venta"
    TRASLADO_SALIDA = "traslado_salida"
    TRASLADO_ENTRADA = "traslado_entrada"


class MotivoEntrada(StrEnum):
    COMPRA = "compra"
    DEVOLUCION_CLIENTE = "devolucion_cliente"
    INVENTARIO_INICIAL = "inventario_inicial"
    PRODUCCION = "produccion"
    OTRO = "otro"


class MotivoSalida(StrEnum):
    PERDIDA = "perdida"
    DETERIORO = "deterioro"
    CONSUMO_INTERNO = "consumo_interno"
    DEVOLUCION_PROVEEDOR = "devolucion_proveedor"
    OTRO = "otro"


class MotivoAjuste(StrEnum):
    CONTEO_FISICO = "conteo_fisico"
    CORRECCION = "correccion"
    OTRO = "otro"


class EstadoVenta(StrEnum):
    REGISTRADA = "registrada"
    ANULADA = "anulada"


class EstadoTraslado(StrEnum):
    SOLICITADO = "solicitado"
    APROBADO = "aprobado"
    CONFIRMADO = "confirmado"
    RECHAZADO = "rechazado"
    CANCELADO = "cancelado"


class TipoAlerta(StrEnum):
    INVENTARIO_BAJO = "inventario_bajo"
    INVENTARIO_EXCESIVO = "inventario_excesivo"
    RIESGO_DESABASTECIMIENTO = "riesgo_desabastecimiento"
    REQUIERE_REVISION = "requiere_revision"


class PrioridadAlerta(StrEnum):
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class EstadoAlerta(StrEnum):
    ACTIVA = "activa"
    RESUELTA = "resuelta"


class EstadoEjecucion(StrEnum):
    EN_COLA = "en_cola"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"


class TipoRecomendacion(StrEnum):
    REABASTECIMIENTO = "reabastecimiento"
    TRASLADO = "traslado"


class EstadoRecomendacion(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    EJECUTADA = "ejecutada"
    REEMPLAZADA = "reemplazada"


class ResultadoAuditoria(StrEnum):
    EXITOSO = "exitoso"
    FALLIDO = "fallido"
