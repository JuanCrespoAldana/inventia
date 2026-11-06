"""Construcción de las respuestas: formatos de números y fechas, y los bloques (métricas, tablas, barras, listas)."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.dto.asistente_dto import (
    Barra,
    Bloque,
    BloqueBarras,
    BloqueLista,
    BloqueMetricas,
    BloqueTabla,
    Celda,
    Columna,
    Enlace,
    Fila,
    Metrica,
    Tono,
)
from app.util.lenguaje import NOMBRES_MES


def _num(valor) -> float:
    return float(valor or 0)


def entero(valor) -> str:
    return f"{round(_num(valor)):,}".replace(",", ".")


def decimal(valor, decimales: int = 1) -> str:
    texto = f"{_num(valor):,.{decimales}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def moneda(valor) -> str:
    n = round(_num(valor))
    return ("-" if n < 0 else "") + "$\u00a0" + f"{abs(n):,}".replace(",", ".")  # espacio duro: «$» y la cifra no se separan al cortar la línea


def porcentaje(valor, decimales: int = 1) -> str:
    return f"{decimal(valor, decimales)}\u00a0%"


def fecha_corta(d: date | datetime | None) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = d.date()
    return f"{d.day} {NOMBRES_MES[d.month][:3]} {d.year}"


def mayuscula_inicial(texto: str) -> str:
    """Solo la primera letra en mayúscula (``str.capitalize`` pasa a minúscula el resto: «Sede Norte» quedaría «Sede norte»)."""
    return texto[:1].upper() + texto[1:]


def n_de(n: int, singular: str, plural: str | None = None) -> str:
    return f"{entero(n)} {singular if n == 1 else (plural or singular + 's')}"


def lista_natural(elementos: list[str]) -> str:
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


@dataclass
class Resp:
    """Lo que produce cada respuesta antes de convertirse en ``RespuestaAsistente``."""

    texto: str
    bloques: list[Bloque] = field(default_factory=list)
    enlaces: list[Enlace] = field(default_factory=list)
    sugerencias: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    entendida: bool = True


def metricas(titulo: str | None, *items: tuple[str, str] | tuple[str, str, str | None] | tuple[str, str, str | None, Tono]) -> BloqueMetricas:
    salida = []
    for item in items:
        etiqueta, valor, *resto = item
        detalle = resto[0] if resto else None
        tono: Tono = resto[1] if len(resto) > 1 else "neutral"  # type: ignore[assignment]
        salida.append(Metrica(etiqueta=etiqueta, valor=valor, detalle=detalle, tono=tono))
    return BloqueMetricas(titulo=titulo, metricas=salida)


def col(clave: str, etiqueta: str, formato: str = "texto", derecha: bool | None = None) -> Columna:
    alinear = "der" if (derecha if derecha is not None else formato in ("entero", "decimal", "moneda", "porcentaje")) else "izq"
    return Columna(clave=clave, etiqueta=etiqueta, formato=formato, alinear=alinear)  # type: ignore[arg-type]


def fila(celdas: dict[str, Celda], *, tonos: dict[str, Tono] | None = None, ruta: str | None = None) -> Fila:
    limpias: dict[str, Celda] = {}
    for k, v in celdas.items():
        if isinstance(v, Decimal):
            v = float(v)
        elif isinstance(v, (date, datetime)):
            v = v.isoformat()
        limpias[k] = v
    return Fila(celdas=limpias, tonos=tonos or {}, ruta=ruta)


def tabla(titulo: str | None, columnas: list[Columna], filas: list[Fila], *, total: int | None = None, nota: str | None = None) -> BloqueTabla:
    return BloqueTabla(titulo=titulo, columnas=columnas, filas=filas, total=len(filas) if total is None else total, nota=nota)


def barras(titulo: str | None, pares: list[tuple[str, float, str]]) -> BloqueBarras:
    return BloqueBarras(titulo=titulo, barras=[Barra(etiqueta=e, valor=float(v), texto=t) for e, v, t in pares])


def lista(titulo: str | None, elementos: list[str]) -> BloqueLista:
    return BloqueLista(titulo=titulo, elementos=elementos)


# Etiquetas y tonos de los valores controlados del dominio (iguales a los de la interfaz).
ESTADO_STOCK: dict[str, tuple[str, Tono]] = {
    "agotado": ("Agotado", "danger"), "bajo": ("Bajo", "warning"), "normal": ("Normal", "success"), "excesivo": ("Excesivo", "accent"),
}
PRIORIDAD: dict[str, tuple[str, Tono]] = {
    "critica": ("Crítica", "danger"), "alta": ("Alta", "warning"), "media": ("Media", "accent"), "baja": ("Baja", "neutral"),
}
TIPO_ALERTA: dict[str, str] = {
    "inventario_bajo": "Inventario bajo", "inventario_excesivo": "Inventario excesivo",
    "riesgo_desabastecimiento": "Riesgo de desabastecimiento", "requiere_revision": "Requiere revisión",
}
ESTADO_TRASLADO: dict[str, tuple[str, Tono]] = {
    "solicitado": ("Solicitado", "warning"), "aprobado": ("Aprobado", "accent"), "confirmado": ("Confirmado", "success"),
    "rechazado": ("Rechazado", "danger"), "cancelado": ("Cancelado", "neutral"),
}
ESTADO_RECOMENDACION: dict[str, tuple[str, Tono]] = {
    "pendiente": ("Pendiente", "warning"), "aprobada": ("Aprobada", "accent"), "rechazada": ("Rechazada", "danger"),
    "ejecutada": ("Ejecutada", "success"), "reemplazada": ("Reemplazada", "neutral"),
}
TIPO_RECOMENDACION: dict[str, str] = {"reabastecimiento": "Reabastecimiento", "traslado": "Traslado entre sedes"}
CONFIANZA: dict[str, tuple[str, Tono]] = {"alta": ("Alta", "success"), "media": ("Media", "accent"), "baja": ("Baja", "warning")}
TIPO_MOVIMIENTO: dict[str, str] = {
    "entrada": "Entrada", "salida": "Salida", "ajuste": "Ajuste", "venta": "Venta", "anulacion_venta": "Anulación de venta",
    "traslado_salida": "Traslado (salida)", "traslado_entrada": "Traslado (entrada)",
}
MOTIVO: dict[str, str] = {
    "compra": "Compra", "devolucion_cliente": "Devolución de cliente", "inventario_inicial": "Inventario inicial", "produccion": "Producción",
    "perdida": "Pérdida", "deterioro": "Deterioro", "consumo_interno": "Consumo interno", "devolucion_proveedor": "Devolución a proveedor",
    "conteo_fisico": "Conteo físico", "correccion": "Corrección", "otro": "Otro",
}
ESTADO_PQRS: dict[str, tuple[str, Tono]] = {
    "pendiente": ("Pendiente", "warning"), "en_revision": ("En revisión", "accent"), "en_proceso": ("En proceso", "accent"), "resuelta": ("Resuelta", "success"),
}
TIPO_PQRS: dict[str, str] = {"peticion": "Petición", "queja": "Queja", "reclamo": "Reclamo", "sugerencia": "Sugerencia"}
ESTADO_NC: dict[str, str] = {
    "reportado": "Reportado", "en_revision": "En revisión", "en_proceso_solucion": "En solución", "resuelto": "Resuelto", "cerrado": "Cerrado",
}
TIPO_NC: dict[str, str] = {
    "defecto_de_fabrica": "Defecto de fábrica", "dano_en_transporte": "Daño en transporte", "producto_equivocado": "Producto equivocado",
    "cantidad_incorrecta": "Cantidad incorrecta", "empaque_deteriorado": "Empaque deteriorado",
    "no_cumple_especificacion": "No cumple la especificación", "otro": "Otro",
}
ESTADO_GARANTIA: dict[str, str] = {
    "reportada": "Reportada", "pendiente_revision": "Pendiente de revisión", "enviada_proveedor": "Enviada al proveedor", "aprobada": "Aprobada",
    "rechazada": "Rechazada", "solucionada": "Solucionada", "cerrada": "Cerrada",
}
TIPO_VEHICULO: dict[str, str] = {
    "bicicleta_electrica": "Bicicleta eléctrica", "patineta_electrica": "Monopatín eléctrico", "motocicleta_electrica": "Moto eléctrica", "otro": "Otro",
}
