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


# ---- Sistema Integrado de Gestión (SIG) ---------------------------------------------------------------


class TipoPqrs(StrEnum):
    PETICION = "peticion"
    QUEJA = "queja"
    RECLAMO = "reclamo"
    SUGERENCIA = "sugerencia"


class EstadoPqrs(StrEnum):
    PENDIENTE = "pendiente"
    EN_REVISION = "en_revision"
    EN_PROCESO = "en_proceso"
    RESUELTA = "resuelta"


class EstadoPausa(StrEnum):
    MOSTRADA = "mostrada"
    REALIZADA = "realizada"
    OMITIDA = "omitida"


class AreaPausa(StrEnum):
    CUELLO = "cuello"
    HOMBROS = "hombros"
    ESPALDA = "espalda"
    MANOS = "manos_munecas"
    OJOS = "ojos"
    PIERNAS = "piernas"
    RESPIRACION = "respiracion"


class TipoNoConformidad(StrEnum):
    DEFECTO_FABRICA = "defecto_de_fabrica"
    DANO_TRANSPORTE = "dano_en_transporte"
    PRODUCTO_EQUIVOCADO = "producto_equivocado"
    CANTIDAD_INCORRECTA = "cantidad_incorrecta"
    EMPAQUE_DETERIORADO = "empaque_deteriorado"
    NO_CUMPLE_ESPECIFICACION = "no_cumple_especificacion"
    OTRO = "otro"


class EstadoNoConformidad(StrEnum):
    REPORTADO = "reportado"
    EN_REVISION = "en_revision"
    EN_SOLUCION = "en_proceso_solucion"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class EstadoGarantia(StrEnum):
    REPORTADA = "reportada"
    PENDIENTE_REVISION = "pendiente_revision"
    ENVIADA_PROVEEDOR = "enviada_proveedor"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    SOLUCIONADA = "solucionada"
    CERRADA = "cerrada"


class TipoDocumentoGarantia(StrEnum):
    FACTURA_COMPRA = "factura_compra"
    ENTRADA_INVENTARIO = "entrada_inventario"
    VENTA = "venta"
    OTRO = "otro"


class TipoVehiculo(StrEnum):
    BICICLETA = "bicicleta_electrica"
    PATINETA = "patineta_electrica"
    MOTOCICLETA = "motocicleta_electrica"
    OTRO = "otro"


class Propulsion(StrEnum):
    ELECTRICA = "electrica"
    ASISTIDA = "asistida_pedaleo"


class EstadoRegistroAmbiental(StrEnum):
    ACTIVO = "activo"
    ANULADO = "anulado"
