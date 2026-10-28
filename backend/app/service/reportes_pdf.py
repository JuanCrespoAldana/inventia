"""Exportación de reportes a PDF (RF-035).

El PDF es para **leer e imprimir**: encabezado con empresa, usuario, fecha y filtros; resumen; tabla con el
encabezado repetido en cada página; y numeración «Página X de Y». Para analizar o procesar los datos completos
se usan Excel o CSV. Por eso el PDF se limita a ``LIMITE_PDF`` filas y lo avisa dentro del documento.

Usa ReportLab con las fuentes estándar del formato (Helvetica), que cubren el español (tildes, ñ, ¿ y ¡).
Los caracteres que esa fuente no puede dibujar se sustituyen por «?» en lugar de salir como un recuadro.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

# «escape» solo prepara el texto para el PDF; no analiza XML externo.
from xml.sax.saxutils import escape  # nosec B406

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as lienzo
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

if TYPE_CHECKING:  # solo para anotaciones; evita una importación circular con reportes_service
    from app.service.reportes_service import Reporte

LIMITE_PDF = 1_000  # el PDF se arma celda por celda: con 2.000 filas tarda ~4 s de CPU; es para leer, no para analizar
AZUL = colors.HexColor("#1F2A44")  # mismo color de encabezado que el Excel
GRIS_CLARO = colors.HexColor("#F2F4F7")
GRIS_LINEA = colors.HexColor("#D0D5DD")
GRIS_TEXTO = colors.HexColor("#475467")
COLUMNAS_PARA_HORIZONTAL = 6  # con más columnas que estas la hoja se pone en horizontal


def _seguro(texto: Any) -> str:
    """Texto que la fuente estándar puede dibujar (Latin-1/Windows-1252). Lo demás pasa a «?»."""
    return str(texto).encode("cp1252", errors="replace").decode("cp1252")


def _miles(valor: float, decimales: int) -> str:
    """Formato es-CO: punto para los miles y coma para los decimales."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _es_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def formatear(valor: Any, tipo: str, decimales_dinero: int = 0) -> str:
    """Convierte un valor del reporte al texto que se imprime. Vacío → «—»."""
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if _es_numero(valor):
        if tipo == "entero":
            return _miles(valor, 0)
        if tipo == "dinero":
            return "$ " + _miles(valor, decimales_dinero)
        if tipo == "decimal":
            return _miles(valor, 2)
        if tipo == "porcentaje":
            return _miles(valor * 100, 1) + " %"
        return _miles(valor, 0) if float(valor).is_integer() else _miles(valor, 2)
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


def _resumen_legible(clave: str, valor: Any) -> str:
    """Los resúmenes son pares «etiqueta: valor»; la etiqueta dice si es dinero o proporción."""
    if _es_numero(valor):
        if clave.lower().startswith(("valor", "total vendido")):
            return "$ " + _miles(valor, 0)
        if "wape" in clave.lower() or "mape" in clave.lower():
            return _miles(valor * 100, 1) + " %"
        return _miles(valor, 0) if float(valor).is_integer() else _miles(valor, 2)
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    return "—" if valor is None or valor == "" else str(valor)


def _decimales_dinero(reporte: Reporte, clave: str) -> int:
    """Si algún valor de la columna tiene centavos, toda la columna se imprime con dos decimales."""
    for fila in reporte.filas:
        v = fila.get(clave)
        if _es_numero(v) and not float(v).is_integer():
            return 2
    return 0


def _anchos(reporte: Reporte, textos: list[list[str]], disponible: float) -> list[float]:
    """Reparte el ancho disponible según lo largo del contenido de cada columna (con mínimo y máximo)."""
    pesos = []
    for j, col in enumerate(reporte.columnas):
        mayor_palabra = max((len(p) for p in _seguro(col.titulo).split()), default=4)
        contenido = max((len(fila[j]) for fila in textos[:300]), default=0)
        pesos.append(min(max(mayor_palabra + 2, contenido, 6), 34))
    total = sum(pesos)
    return [disponible * p / total for p in pesos]


class _LienzoNumerado(lienzo.Canvas):
    """Dibuja el pie «Página X de Y»; el total solo se conoce al terminar, por eso guarda cada página."""

    pie_izquierdo = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas: list[dict] = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self._pie(total)
            super().showPage()
        super().save()

    def _pie(self, total: int) -> None:
        ancho, _ = self._pagesize
        self.setStrokeColor(GRIS_LINEA)
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, ancho - 15 * mm, 12 * mm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRIS_TEXTO)
        self.drawString(15 * mm, 8 * mm, self.pie_izquierdo)
        self.drawRightString(ancho - 15 * mm, 8 * mm, f"Página {self._pageNumber} de {total}")


def a_pdf(reporte: Reporte, *, empresa: str, usuario: str, filtros_texto: str, generado: datetime) -> bytes:
    horizontal = len(reporte.columnas) > COLUMNAS_PARA_HORIZONTAL
    tamano = landscape(A4) if horizontal else portrait(A4)
    margen = 15 * mm
    disponible = tamano[0] - 2 * margen
    tam_letra = 7.5 if len(reporte.columnas) > 9 else 8

    titulo = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=AZUL)
    empresa_estilo = ParagraphStyle("empresa", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=GRIS_TEXTO)
    meta = ParagraphStyle("meta", fontName="Helvetica", fontSize=8, leading=11, textColor=GRIS_TEXTO)
    aviso = ParagraphStyle("aviso", fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=colors.HexColor("#B54708"))
    encabezado = ParagraphStyle("enc", fontName="Helvetica-Bold", fontSize=tam_letra, leading=tam_letra + 2, textColor=colors.white)
    celda = ParagraphStyle("celda", fontName="Helvetica", fontSize=tam_letra, leading=tam_letra + 2, alignment=TA_LEFT)
    celda_der = ParagraphStyle("celda_der", parent=celda, alignment=TA_RIGHT)
    encabezado_der = ParagraphStyle("enc_der", parent=encabezado, alignment=TA_RIGHT)
    clave_resumen = ParagraphStyle("clave", fontName="Helvetica-Bold", fontSize=8, leading=10.5)
    valor_resumen = ParagraphStyle("valor", fontName="Helvetica", fontSize=8, leading=10.5)

    def p(texto: Any, estilo: ParagraphStyle) -> Paragraph:
        return Paragraph(escape(_seguro(texto)), estilo)

    historia: list = [p(empresa, empresa_estilo), p(reporte.titulo, titulo), Spacer(1, 2 * mm)]
    linea = f"Generado por {usuario} el {generado.strftime('%d/%m/%Y %H:%M')}"
    historia.append(p(linea, meta))
    historia.append(p(f"Filtros: {filtros_texto or 'sin filtros'}", meta))
    historia.append(p(f"Filas incluidas: {_miles(len(reporte.filas), 0)}", meta))

    if reporte.resumen:
        historia.append(Spacer(1, 4 * mm))
        filas_resumen = [[p(k, clave_resumen), p(_resumen_legible(k, v), valor_resumen)] for k, v in reporte.resumen.items()]
        resumen = Table(filas_resumen, colWidths=[min(80 * mm, disponible * 0.45), disponible - min(80 * mm, disponible * 0.45)])
        resumen.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO), ("LINEBELOW", (0, 0), (-1, -1), 0.25, GRIS_LINEA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        historia.append(resumen)

    if reporte.truncado:
        historia.append(Spacer(1, 3 * mm))
        historia.append(p(
            f"Este PDF muestra solo las primeras {_miles(len(reporte.filas), 0)} filas y hay más; el resumen de arriba suma solo esas filas. "
            "Para el reporte completo use la descarga en Excel o CSV, o acote las fechas.", aviso,
        ))
    historia.append(Spacer(1, 5 * mm))

    if not reporte.filas:
        historia.append(p("No hay datos para los filtros elegidos.", meta))
    else:
        decimales = {c.clave: _decimales_dinero(reporte, c.clave) for c in reporte.columnas if c.tipo == "dinero"}
        textos = [[formatear(f.get(c.clave), c.tipo, decimales.get(c.clave, 0)) for c in reporte.columnas] for f in reporte.filas]
        derecha = [c.tipo in ("entero", "dinero", "decimal", "porcentaje") for c in reporte.columnas]
        cuerpo = [[p(c.titulo, encabezado_der if derecha[j] else encabezado) for j, c in enumerate(reporte.columnas)]]
        for fila in textos:
            cuerpo.append([p(t, celda_der if derecha[j] else celda) for j, t in enumerate(fila)])
        tabla = Table(cuerpo, colWidths=_anchos(reporte, textos, disponible), repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, GRIS_LINEA),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        estilo += [("BACKGROUND", (0, i), (-1, i), GRIS_CLARO) for i in range(2, len(cuerpo), 2)]
        tabla.setStyle(TableStyle(estilo))
        historia.append(tabla)

    salida = io.BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=tamano, leftMargin=margen, rightMargin=margen, topMargin=14 * mm, bottomMargin=18 * mm,
        title=_seguro(f"{reporte.titulo} — {empresa}"), author=_seguro(usuario), subject="Reporte de Inventia", creator="Inventia",
    )
    pie = _seguro(f"Inventia · {empresa}")

    class Lienzo(_LienzoNumerado):
        pie_izquierdo = pie

    documento.build(historia, canvasmaker=Lienzo)
    return salida.getvalue()
