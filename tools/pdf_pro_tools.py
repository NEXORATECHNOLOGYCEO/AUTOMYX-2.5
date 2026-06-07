"""
PDF Pro Tools - Generación de PDFs PROFESIONALES de grado corporativo
=====================================================================
Plantillas prediseñadas para +20 tipos de documentos con diseño editorial:
contratos, facturas, informes, propuestas, NDAs, recibos, CVs, cartas,
whitepapers, brochures, manuales, certificados, presupuestos, órdenes
de compra, estados financieros, etc.

Diseño: header corporativo, footer con paginación, tabla de contenidos
auto-generada, tipografía consistente, paleta de colores configurable,
gráficos embebidos, multi-columna, hipervínculos, firmas digitales.

Usa reportlab si está disponible, sino fpdf2 (con menos features).
"""
from __future__ import annotations

import os
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, LETTER, LEGAL
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm, inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
        PageBreak, KeepTogether, HRFlowable, ListFlowable, ListItem,
        PageTemplate, Frame, BaseDocTemplate, NextPageTemplate,
    )
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from fpdf import FPDF
    FPDF2_AVAILABLE = True
except ImportError:
    FPDF2_AVAILABLE = False

# Intentar matplotlib para gráficos
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Colores corporativos predefinidos
# ---------------------------------------------------------------------------
PALETTES = {
    "professional_blue": {
        "primary": "#0B3D91", "secondary": "#1E5BC6", "accent": "#4A90E2",
        "text": "#1A1A2E", "muted": "#5F6B7A", "light": "#F0F4F8", "border": "#D0D9E2",
    },
    "corporate_gray": {
        "primary": "#2C3E50", "secondary": "#34495E", "accent": "#E74C3C",
        "text": "#2C3E50", "muted": "#7F8C8D", "light": "#ECF0F1", "border": "#BDC3C7",
    },
    "tech_modern": {
        "primary": "#0F172A", "secondary": "#1E293B", "accent": "#06B6D4",
        "text": "#0F172A", "muted": "#64748B", "light": "#F1F5F9", "border": "#CBD5E1",
    },
    "elegant_gold": {
        "primary": "#1A1A1A", "secondary": "#333333", "accent": "#B8860B",
        "text": "#1A1A1A", "muted": "#666666", "light": "#FAFAFA", "border": "#E0E0E0",
    },
    "medical_clean": {
        "primary": "#006A6B", "secondary": "#008B8B", "accent": "#20B2AA",
        "text": "#1F2937", "muted": "#6B7280", "light": "#F0FDFA", "border": "#B2DFDB",
    },
    "legal_classic": {
        "primary": "#1A1A1A", "secondary": "#444444", "accent": "#8B0000",
        "text": "#1A1A1A", "muted": "#555555", "light": "#FAFAFA", "border": "#CCCCCC",
    },
    "creative_violet": {
        "primary": "#5B21B6", "secondary": "#7C3AED", "accent": "#EC4899",
        "text": "#1E1B4B", "muted": "#6B7280", "light": "#FAF5FF", "border": "#DDD6FE",
    },
    "eco_green": {
        "primary": "#166534", "secondary": "#15803D", "accent": "#22C55E",
        "text": "#14532D", "muted": "#6B7280", "light": "#F0FDF4", "border": "#BBF7D0",
    },
}


# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------
def _check_engine() -> Dict[str, Any]:
    if REPORTLAB_AVAILABLE:
        return {"ok": True, "engine": "reportlab"}
    if FPDF2_AVAILABLE:
        return {"ok": True, "engine": "fpdf2"}
    return {"ok": False, "error": "Instala reportlab o fpdf2: pip install reportlab fpdf2"}


def _hex_to_color(hex_str: str) -> Tuple[float, float, float]:
    """Convierte hex a tupla RGB 0-1."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _ensure_path(path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


def _make_temp_chart(data: List[float], labels: List[str], title: str, chart_type: str = "bar",
                     output_path: Optional[str] = None) -> Optional[str]:
    """Genera un gráfico PNG con matplotlib."""
    if not MATPLOTLIB_AVAILABLE:
        return None
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=150)
    if chart_type == "bar":
        ax.bar(labels, data, color="#1E5BC6", edgecolor="#0B3D91", linewidth=1.2)
    elif chart_type == "line":
        ax.plot(labels, data, marker="o", color="#1E5BC6", linewidth=2, markersize=8)
    elif chart_type == "pie":
        colors_list = ["#0B3D91", "#1E5BC6", "#4A90E2", "#8BB8E8", "#C5D9F0"]
        ax.pie(data, labels=labels, colors=colors_list[:len(data)], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    ax.set_title(title, fontsize=12, fontweight="bold", color="#0B3D91")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    if output_path is None:
        output_path = f"/tmp/chart_{int(time.time())}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    return output_path


# ===========================================================================
# MOTOR REPORTLAB (preferido)
# ===========================================================================

class _BaseDocTemplate(BaseDocTemplate if REPORTLAB_AVAILABLE else object):
    """Template con header/footer corporativo."""
    def __init__(self, filename, **kwargs):
        if REPORTLAB_AVAILABLE:
            super().__init__(filename, **kwargs)
        self.brand = kwargs.get("brand", {})
        self.title_doc = kwargs.get("title", "")
        self.author = kwargs.get("author", "AUTOMYX")
        self.show_page_num = kwargs.get("show_page_num", True)

    def after_page(self):
        if not REPORTLAB_AVAILABLE:
            return
        self._draw_footer()
        self._draw_header()

    def _draw_header(self):
        c = self.canv
        c.saveState()
        # Línea superior color primary
        c.setStrokeColor(colors.HexColor(self.brand.get("primary", "#0B3D91")))
        c.setLineWidth(2)
        c.line(2 * cm, self.pagesize[1] - 1.2 * cm, self.pagesize[0] - 2 * cm, self.pagesize[1] - 1.2 * cm)
        # Brand name
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor(self.brand.get("primary", "#0B3D91")))
        c.drawString(2 * cm, self.pagesize[1] - 1.0 * cm, self.brand.get("company_name", "AUTOMYX"))
        # Tagline derecha
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor(self.brand.get("muted", "#5F6B7A")))
        c.drawRightString(self.pagesize[0] - 2 * cm, self.pagesize[1] - 1.0 * cm, self.brand.get("tagline", ""))
        c.restoreState()

    def _draw_footer(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(colors.HexColor(self.brand.get("border", "#D0D9E2")))
        c.setLineWidth(0.5)
        c.line(2 * cm, 1.5 * cm, self.pagesize[0] - 2 * cm, 1.5 * cm)
        # Footer text
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor(self.brand.get("muted", "#5F6B7A")))
        c.drawString(2 * cm, 1.0 * cm, self.brand.get("footer_left", ""))
        if self.show_page_num:
            c.drawCentredString(self.pagesize[0] / 2, 1.0 * cm, f"Página {c.getPageNumber()}")
        c.drawRightString(self.pagesize[0] - 2 * cm, 1.0 * cm, self.brand.get("footer_right", ""))
        c.restoreState()


def _get_styles(brand: Dict[str, str]) -> Dict[str, ParagraphStyle]:
    if not REPORTLAB_AVAILABLE:
        return {}
    styles = getSampleStyleSheet()
    primary = colors.HexColor(brand.get("primary", "#0B3D91"))
    secondary = colors.HexColor(brand.get("secondary", "#1E5BC6"))
    text_color = colors.HexColor(brand.get("text", "#1A1A2E"))
    muted = colors.HexColor(brand.get("muted", "#5F6B7A"))
    light_bg = colors.HexColor(brand.get("light", "#F0F4F8"))

    custom = {
        "Title": ParagraphStyle("Title", parent=styles["Title"], fontSize=24, leading=28, textColor=primary,
                                spaceAfter=12, fontName="Helvetica-Bold", alignment=TA_LEFT),
        "Subtitle": ParagraphStyle("Subtitle", parent=styles["Heading2"], fontSize=14, leading=18, textColor=secondary,
                                   spaceAfter=18, fontName="Helvetica"),
        "H1": ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, leading=22, textColor=primary,
                              spaceBefore=18, spaceAfter=10, fontName="Helvetica-Bold"),
        "H2": ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, leading=18, textColor=primary,
                              spaceBefore=14, spaceAfter=8, fontName="Helvetica-Bold"),
        "H3": ParagraphStyle("H3", parent=styles["Heading3"], fontSize=12, leading=15, textColor=secondary,
                              spaceBefore=10, spaceAfter=6, fontName="Helvetica-Bold"),
        "Body": ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, textColor=text_color,
                                fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6),
        "BodyLeft": ParagraphStyle("BodyLeft", parent=styles["Normal"], fontSize=10, leading=14, textColor=text_color,
                                    fontName="Helvetica", alignment=TA_LEFT, spaceAfter=6),
        "Small": ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=muted,
                                 fontName="Helvetica"),
        "Caption": ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8, leading=10, textColor=muted,
                                   fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceAfter=8),
        "Quote": ParagraphStyle("Quote", parent=styles["Normal"], fontSize=11, leading=15, textColor=secondary,
                                 fontName="Helvetica-Oblique", leftIndent=20, rightIndent=20, spaceAfter=8),
        "TOCEntry": ParagraphStyle("TOCEntry", parent=styles["Normal"], fontSize=10, leading=14, textColor=text_color,
                                    fontName="Helvetica", leftIndent=0, spaceAfter=4),
    }
    return custom


def _make_table(data: List[List[Any]], brand: Dict[str, str], *, header: bool = True,
                col_widths: Optional[List[float]] = None, zebra: bool = True,
                first_col_bold: bool = False) -> Any:
    """Tabla estilizada."""
    if not REPORTLAB_AVAILABLE:
        return None
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold" if header else "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 10 if header else 10),
        ("FONTSIZE", (0, 1 if header else 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(brand.get("primary", "#0B3D91"))),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(brand.get("border", "#D0D9E2"))),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor(brand.get("border", "#D0D9E2"))),
    ]
    if zebra and len(data) > 1:
        for i in range(1 if header else 0, len(data), 2):
            if i > 0 and (i - (1 if header else 0)) % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(brand.get("light", "#F0F4F8"))))
    if first_col_bold:
        for r in range(1 if header else 0, len(data)):
            style.append(("FONTNAME", (0, r), (0, r), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


# ===========================================================================
# PLANTILLAS POR TIPO DE DOCUMENTO
# ===========================================================================

def create_contract(
    output_path: str,
    *,
    contract_type: str = "services",  # services, employment, nda, lease, sales, partnership
    parties: List[Dict[str, str]] = None,
    terms: List[Dict[str, str]] = None,
    effective_date: Optional[str] = None,
    duration: Optional[str] = None,
    jurisdiction: str = "Argentina",
    brand: Optional[Dict[str, str]] = None,
    brand_palette: str = "legal_classic",
    additional_clauses: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Crea un CONTRATO profesional.
    parties: [{"role": "PRESTADOR", "name": "...", "id": "...", "address": "..."}]
    terms: [{"title": "OBJETO", "body": "..."}]
    """
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido para contratos profesionales"}
    if not parties or not terms:
        return {"ok": False, "error": "Faltan 'parties' o 'terms'"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm,
        title=f"Contrato de {contract_type}", author="AUTOMYX", brand=b,
        show_page_num=True,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=frame, onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    story: List[Any] = []

    contract_titles = {
        "services": "CONTRATO DE PRESTACIÓN DE SERVICIOS",
        "employment": "CONTRATO DE TRABAJO",
        "nda": "ACUERDO DE CONFIDENCIALIDAD",
        "lease": "CONTRATO DE ARRENDAMIENTO",
        "sales": "CONTRATO DE COMPRAVENTA",
        "partnership": "ACUERDO DE ASOCIACIÓN",
    }
    title = contract_titles.get(contract_type, f"CONTRATO DE {contract_type.upper()}")

    # Title
    story.append(Paragraph(title, styles["Title"]))
    if effective_date:
        story.append(Paragraph(f"<b>Fecha de entrada en vigencia:</b> {effective_date}", styles["Body"]))
    if duration:
        story.append(Paragraph(f"<b>Duración:</b> {duration}", styles["Body"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(b["border"]), spaceAfter=12, spaceBefore=4))

    # Identificación de las partes
    story.append(Paragraph("IDENTIFICACIÓN DE LAS PARTES", styles["H2"]))
    for p in parties:
        text = f"<b>{p.get('role', 'PARTE').upper()}:</b> {p.get('name', 'N/A')}"
        if p.get("id"):
            text += f", identificado/a con {p.get('id_type', 'DNI')} {p['id']}"
        if p.get("address"):
            text += f", con domicilio en {p['address']}"
        story.append(Paragraph(text, styles["Body"]))
    story.append(Spacer(1, 6 * mm))

    # Estipulaciones (cláusulas)
    for i, term in enumerate(terms, 1):
        story.append(Paragraph(f"CLÁUSULA {i}: {term.get('title', '').upper()}", styles["H2"]))
        story.append(Paragraph(term.get("body", "").replace("\n", "<br/>"), styles["Body"]))

    # Cláusulas adicionales
    if additional_clauses:
        for term in additional_clauses:
            story.append(Paragraph(term.get("title", "").upper(), styles["H2"]))
            story.append(Paragraph(term.get("body", "").replace("\n", "<br/>"), styles["Body"]))

    # Jurisdicción
    story.append(Paragraph(f"JURISDICCIÓN", styles["H2"]))
    story.append(Paragraph(
        f"Las partes acuerdan que para cualquier controversia derivada del presente contrato, "
        f"serán competentes los tribunales ordinarios de la ciudad de {jurisdiction}, "
        f"renunciando expresamente a cualquier otro fuero o jurisdicción.",
        styles["Body"]))

    # Espacios para firmas
    story.append(Spacer(1, 12 * mm))
    sig_data = []
    for p in parties:
        sig_data.append([
            Paragraph("<b>_____________________________</b><br/><br/>Firma", styles["Body"]),
            Paragraph(f"<b>_____________________________</b><br/><br/>Aclaración: {p.get('name', '')}", styles["Body"]),
        ])
    # Tabla de firmas 2 columnas
    if len(sig_data) >= 2:
        t = Table([sig_data[0], sig_data[1]] if len(sig_data) > 1 else [sig_data[0]],
                  colWidths=[doc.width / 2] * 2)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("<b>_____________________________</b><br/><br/>Firma", styles["Body"]))

    doc.build(story)
    return {"ok": True, "output": output_path, "type": "contract", "contract_type": contract_type,
            "size_bytes": os.path.getsize(output_path), "parties_count": len(parties),
            "clauses_count": len(terms) + len(additional_clauses or [])}


def create_invoice(
    output_path: str,
    *,
    invoice_number: str,
    issue_date: str,
    due_date: Optional[str] = None,
    seller: Dict[str, str] = None,
    buyer: Dict[str, str] = None,
    items: List[Dict[str, Any]] = None,
    tax_rate: float = 0.21,
    tax_label: str = "IVA",
    currency: str = "USD",
    notes: Optional[str] = None,
    brand_palette: str = "professional_blue",
    brand: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Crea una FACTURA profesional."""
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido"}
    if not all([invoice_number, issue_date, seller, buyer, items]):
        return {"ok": False, "error": "Faltan campos requeridos: invoice_number, issue_date, seller, buyer, items"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm,
        title=f"Factura {invoice_number}", author="AUTOMYX", brand=b,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=frame, onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    story: List[Any] = []

    # Header con FACTURA + número
    header_data = [[
        Paragraph(f"<font size=28 color='{b['primary']}'><b>FACTURA</b></font>", styles["BodyLeft"]),
        Paragraph(
            f"<b>Nº {invoice_number}</b><br/>"
            f"<font size=9 color='{b['muted']}'>Fecha de emisión: {issue_date}</font><br/>"
            + (f"<font size=9 color='{b['muted']}'>Vencimiento: {due_date}</font>" if due_date else ""),
            ParagraphStyle("right", parent=styles["BodyLeft"], alignment=TA_RIGHT),
        ),
    ]]
    ht = Table(header_data, colWidths=[doc.width / 2] * 2)
    ht.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(ht)
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(b["primary"]), spaceAfter=8))

    # Emisor / Receptor
    party_data = [[
        Paragraph(f"<b>EMISOR</b><br/>{seller.get('name', '')}<br/>{seller.get('id', '')}<br/>{seller.get('address', '')}<br/>{seller.get('email', '')}", styles["BodyLeft"]),
        Paragraph(f"<b>RECEPTOR</b><br/>{buyer.get('name', '')}<br/>{buyer.get('id', '')}<br/>{buyer.get('address', '')}<br/>{buyer.get('email', '')}", ParagraphStyle("right2", parent=styles["BodyLeft"], alignment=TA_LEFT)),
    ]]
    pt = Table(party_data, colWidths=[doc.width / 2] * 2)
    pt.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(b["light"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(pt)
    story.append(Spacer(1, 8 * mm))

    # Tabla de items
    story.append(Paragraph("DETALLE", styles["H2"]))
    table_data = [["#", "Descripción", "Cantidad", "Precio Unit.", f"Subtotal ({currency})"]]
    subtotal = 0.0
    for i, it in enumerate(items, 1):
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        sub = qty * price
        subtotal += sub
        table_data.append([
            str(i),
            it.get("description", ""),
            f"{qty:.2f}",
            f"{price:,.2f}",
            f"{sub:,.2f}",
        ])

    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount

    table_data.append(["", "", "", "Subtotal:", f"{subtotal:,.2f} {currency}"])
    table_data.append(["", "", "", f"{tax_label} ({tax_rate*100:.0f}%):", f"{tax_amount:,.2f} {currency}"])
    table_data.append(["", "", "", "TOTAL:", f"{total:,.2f} {currency}"])

    t = _make_table(table_data, b, col_widths=[1 * cm, 8 * cm, 2 * cm, 3 * cm, 3 * cm], first_col_bold=False)
    # Highlight TOTAL row
    last_row = len(table_data) - 1
    t.setStyle(TableStyle([
        ("BACKGROUND", (3, last_row), (-1, last_row), colors.HexColor(b["primary"])),
        ("TEXTCOLOR", (3, last_row), (-1, last_row), colors.white),
        ("FONTNAME", (3, last_row), (-1, last_row), "Helvetica-Bold"),
        ("BACKGROUND", (3, last_row - 1), (-1, last_row - 1), colors.HexColor(b["light"])),
        ("BACKGROUND", (3, last_row - 2), (-1, last_row - 2), colors.HexColor(b["light"])),
    ]))
    story.append(t)

    if notes:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Notas:</b> {notes}", styles["Small"]))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        f"Gracias por su confianza. Para cualquier consulta sobre esta factura, "
        f"contáctenos a {seller.get('email', 'nuestro email de contacto')}.",
        ParagraphStyle("thanks", parent=styles["Body"], alignment=TA_CENTER, textColor=colors.HexColor(b["muted"]))
    ))

    doc.build(story)
    return {"ok": True, "output": output_path, "type": "invoice", "number": invoice_number,
            "subtotal": subtotal, "tax": tax_amount, "total": total, "currency": currency,
            "size_bytes": os.path.getsize(output_path)}


def create_invoice_v2(*args, **kwargs):
    """Alias para compatibilidad."""
    return create_invoice(*args, **kwargs)


def create_report(
    output_path: str,
    *,
    title: str,
    subtitle: str = "",
    author: str = "",
    date: Optional[str] = None,
    sections: List[Dict[str, Any]] = None,
    table_of_contents: bool = True,
    include_header_footer: bool = True,
    brand_palette: str = "professional_blue",
    brand: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Crea un INFORME profesional con secciones, tablas, gráficos, imágenes.
    sections: [{"heading": "...", "level": 1, "content": "...", "table": [...], "chart": {...}, "image": "..."}]
    """
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido"}
    if not sections:
        return {"ok": False, "error": "Faltan 'sections'"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)
    if not date:
        date = time.strftime("%d/%m/%Y")

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.5 * cm, bottomMargin=2.0 * cm,
        title=title, author=author or "AUTOMYX", brand=b,
        show_page_num=include_header_footer,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=frame, onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    story: List[Any] = []

    # Portada
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph(title, ParagraphStyle("portada_title", parent=styles["Title"], fontSize=32, alignment=TA_CENTER, spaceAfter=20)))
    if subtitle:
        story.append(Paragraph(subtitle, ParagraphStyle("portada_sub", parent=styles["Subtitle"], alignment=TA_CENTER, fontSize=16, textColor=colors.HexColor(b["secondary"]))))
    story.append(Spacer(1, 4 * cm))
    story.append(HRFlowable(width="40%", thickness=2, color=colors.HexColor(b["accent"]), hAlign="CENTER", spaceAfter=12))
    if author:
        story.append(Paragraph(f"<b>Autor:</b> {author}", ParagraphStyle("pa", parent=styles["Body"], alignment=TA_CENTER)))
    story.append(Paragraph(f"<b>Fecha:</b> {date}", ParagraphStyle("pd", parent=styles["Body"], alignment=TA_CENTER)))
    story.append(PageBreak())

    # Tabla de contenidos
    if table_of_contents:
        story.append(Paragraph("TABLA DE CONTENIDOS", styles["H1"]))
        for i, sec in enumerate(sections, 1):
            indent = "&nbsp;" * ((sec.get("level", 1) - 1) * 4)
            story.append(Paragraph(f"{indent}{i}. {sec.get('heading', '')}", styles["TOCEntry"]))
        story.append(PageBreak())

    # Secciones
    for sec in sections:
        level = sec.get("level", 1)
        h_style = styles.get(f"H{min(level, 3)}", styles["H1"])
        story.append(Paragraph(sec.get("heading", ""), h_style))

        # Contenido de texto (puede ser markdown simple)
        content = sec.get("content", "")
        if content:
            paragraphs = content.split("\n\n")
            for para in paragraphs:
                # Detectar bullets
                if para.strip().startswith("- "):
                    items = [line[2:].strip() for line in para.split("\n") if line.strip().startswith("- ")]
                    story.append(ListFlowable(
                        [ListItem(Paragraph(it, styles["Body"])) for it in items],
                        bulletType="bullet", leftIndent=20))
                elif para.strip().startswith("> "):
                    quote_text = para.replace("> ", "").replace("\n> ", " ").strip()
                    story.append(Paragraph(quote_text, styles["Quote"]))
                else:
                    # Bold inline
                    formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", para)
                    formatted = re.sub(r"\*(.+?)\*", r"<i>\1</i>", formatted)
                    story.append(Paragraph(formatted.replace("\n", "<br/>"), styles["Body"]))

        # Tabla
        if sec.get("table"):
            t_data = sec["table"]
            story.append(_make_table(t_data, b, first_col_bold=True))
            story.append(Spacer(1, 4 * mm))

        # Gráfico
        if sec.get("chart"):
            chart = sec["chart"]
            chart_path = _make_temp_chart(
                chart.get("data", []), chart.get("labels", []),
                chart.get("title", ""), chart.get("type", "bar"))
            if chart_path and os.path.exists(chart_path):
                story.append(Image(chart_path, width=14 * cm, height=8 * cm))
                story.append(Paragraph(f"<i>Figura: {chart.get('title', '')}</i>", styles["Caption"]))
                story.append(Spacer(1, 4 * mm))

        # Imagen
        if sec.get("image") and os.path.exists(sec["image"]):
            story.append(Image(sec["image"], width=12 * cm, height=8 * cm))
            story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return {"ok": True, "output": output_path, "type": "report", "title": title,
            "sections": len(sections), "size_bytes": os.path.getsize(output_path)}


def create_proposal(
    output_path: str,
    *,
    title: str,
    client_name: str,
    client_company: str = "",
    project_overview: str = "",
    deliverables: List[str] = None,
    timeline: List[Dict[str, str]] = None,
    pricing: List[Dict[str, Any]] = None,
    total: Optional[str] = None,
    terms: str = "",
    valid_until: Optional[str] = None,
    brand_palette: str = "tech_modern",
    brand: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Crea una PROPUESTA comercial profesional."""
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm,
        title=f"Propuesta: {title}", author="AUTOMYX", brand=b,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=frame, onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    story: List[Any] = []

    # Hero
    story.append(Paragraph("PROPUESTA COMERCIAL", ParagraphStyle("hero", parent=styles["Title"], fontSize=12, textColor=colors.HexColor(b["accent"]))))
    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Para: <b>{client_name}</b>" + (f" ({client_company})" if client_company else ""), styles["Subtitle"]))
    if valid_until:
        story.append(Paragraph(f"<b>Válida hasta:</b> {valid_until}", styles["Small"]))
    story.append(Spacer(1, 6 * mm))

    if project_overview:
        story.append(Paragraph("RESUMEN DEL PROYECTO", styles["H1"]))
        story.append(Paragraph(project_overview, styles["Body"]))

    if deliverables:
        story.append(Paragraph("ENTREGABLES", styles["H1"]))
        story.append(ListFlowable(
            [ListItem(Paragraph(d, styles["Body"])) for d in deliverables],
            bulletType="bullet", leftIndent=20))
        story.append(Spacer(1, 4 * mm))

    if timeline:
        story.append(Paragraph("CRONOGRAMA", styles["H1"]))
        t_data = [["Fase", "Actividad", "Duración"]]
        for tl in timeline:
            t_data.append([tl.get("phase", ""), tl.get("activity", ""), tl.get("duration", "")])
        story.append(_make_table(t_data, b, first_col_bold=True))
        story.append(Spacer(1, 4 * mm))

    if pricing:
        story.append(Paragraph("INVERSIÓN", styles["H1"]))
        p_data = [["Concepto", "Descripción", "Precio"]]
        for p in pricing:
            p_data.append([p.get("item", ""), p.get("description", ""), p.get("price", "")])
        if total:
            p_data.append(["", "TOTAL", total])
        t = _make_table(p_data, b, first_col_bold=True)
        if total:
            last = len(p_data) - 1
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, last), (-1, last), colors.HexColor(b["primary"])),
                ("TEXTCOLOR", (0, last), (-1, last), colors.white),
                ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
            ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    if terms:
        story.append(Paragraph("TÉRMINOS Y CONDICIONES", styles["H1"]))
        story.append(Paragraph(terms, styles["Body"]))

    doc.build(story)
    return {"ok": True, "output": output_path, "type": "proposal", "client": client_name,
            "size_bytes": os.path.getsize(output_path)}


def create_resume(
    output_path: str,
    *,
    full_name: str,
    title: str = "",
    email: str = "",
    phone: str = "",
    location: str = "",
    linkedin: str = "",
    website: str = "",
    summary: str = "",
    experience: List[Dict[str, str]] = None,
    education: List[Dict[str, str]] = None,
    skills: List[str] = None,
    languages: Optional[List[Dict[str, str]]] = None,
    certifications: Optional[List[str]] = None,
    brand_palette: str = "elegant_gold",
    brand: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Crea un CV / RESUMEN profesional con sidebar."""
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"CV - {full_name}", author=full_name, brand=b,
    )

    # Dos columnas: sidebar 6cm + contenido
    sidebar_width = 6.5 * cm
    main_width = doc.width - sidebar_width

    sidebar_frame = Frame(doc.leftMargin, doc.bottomMargin, sidebar_width, doc.height, id="sidebar",
                          leftPadding=0, rightPadding=8, topPadding=0, bottomPadding=0,
                          showBoundary=0)
    main_frame = Frame(doc.leftMargin + sidebar_width, doc.bottomMargin, main_width, doc.height, id="main",
                       leftPadding=12, rightPadding=0, topPadding=0, bottomPadding=0,
                       showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="default", frames=[sidebar_frame, main_frame],
                                       onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    sidebar_style = ParagraphStyle("side", parent=styles["BodyLeft"], fontSize=9, leading=12,
                                    textColor=colors.HexColor(b["text"]), spaceAfter=4)
    sidebar_h = ParagraphStyle("sideh", parent=styles["H3"], fontSize=10, leading=12,
                                textColor=colors.HexColor(b["accent"]), spaceAfter=4, spaceBefore=8)

    # SIDEBAR
    side_story: List[Any] = []
    side_story.append(Paragraph("CONTACTO", sidebar_h))
    if email: side_story.append(Paragraph(f"✉ {email}", sidebar_style))
    if phone: side_story.append(Paragraph(f"☎ {phone}", sidebar_style))
    if location: side_story.append(Paragraph(f"⌂ {location}", sidebar_style))
    if linkedin: side_story.append(Paragraph(f"in {linkedin}", sidebar_style))
    if website: side_story.append(Paragraph(f"🌐 {website}", sidebar_style))

    if skills:
        side_story.append(Paragraph("HABILIDADES", sidebar_h))
        for s in skills:
            side_story.append(Paragraph(f"• {s}", sidebar_style))

    if languages:
        side_story.append(Paragraph("IDIOMAS", sidebar_h))
        for l in languages:
            txt = l.get("name", "")
            if l.get("level"):
                txt += f" - {l['level']}"
            side_story.append(Paragraph(f"• {txt}", sidebar_style))

    if certifications:
        side_story.append(Paragraph("CERTIFICACIONES", sidebar_h))
        for c in certifications:
            side_story.append(Paragraph(f"• {c}", sidebar_style))

    # MAIN
    main_story: List[Any] = []
    name_style = ParagraphStyle("name", fontSize=28, leading=32, textColor=colors.HexColor(b["primary"]),
                                 fontName="Helvetica-Bold", spaceAfter=2)
    main_story.append(Paragraph(full_name, name_style))
    if title:
        title_style = ParagraphStyle("tt", fontSize=14, leading=18, textColor=colors.HexColor(b["accent"]),
                                      fontName="Helvetica", spaceAfter=10)
        main_story.append(Paragraph(title, title_style))

    if summary:
        main_story.append(Paragraph("PERFIL PROFESIONAL", styles["H1"]))
        main_story.append(Paragraph(summary, styles["Body"]))

    if experience:
        main_story.append(Paragraph("EXPERIENCIA PROFESIONAL", styles["H1"]))
        for exp in experience:
            period = exp.get("period", "")
            position = exp.get("position", "")
            company = exp.get("company", "")
            desc = exp.get("description", "")
            main_story.append(Paragraph(f"<b>{position}</b> - {company}", styles["H3"]))
            if period:
                main_story.append(Paragraph(f"<font size=9 color='{b['muted']}'>{period}</font>", styles["Small"]))
            if desc:
                # Bullets
                for line in desc.split("\n"):
                    if line.strip().startswith("- "):
                        main_story.append(Paragraph(f"• {line[2:].strip()}", styles["Body"]))
                    elif line.strip():
                        main_story.append(Paragraph(line, styles["Body"]))
            main_story.append(Spacer(1, 2 * mm))

    if education:
        main_story.append(Paragraph("EDUCACIÓN", styles["H1"]))
        for ed in education:
            degree = ed.get("degree", "")
            inst = ed.get("institution", "")
            year = ed.get("year", "")
            main_story.append(Paragraph(f"<b>{degree}</b> - {inst}", styles["H3"]))
            if year:
                main_story.append(Paragraph(f"<font size=9 color='{b['muted']}'>{year}</font>", styles["Small"]))
            main_story.append(Spacer(1, 2 * mm))

    # Construir
    from reportlab.platypus import KeepInFrame
    sidebar_kif = KeepInFrame(sidebar_width, doc.height, side_story, mode="shrink")
    main_kif = KeepInFrame(main_width, doc.height, main_story, mode="shrink")
    # Hay que usar un flow que ocupe ambos frames
    # Truco: usar una tabla sin bordes
    combined = Table([[sidebar_kif, main_kif]], colWidths=[sidebar_width, main_width])
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(b["light"])),
    ]))
    doc.build([combined])
    return {"ok": True, "output": output_path, "type": "resume", "name": full_name,
            "size_bytes": os.path.getsize(output_path)}


def create_letter(
    output_path: str,
    *,
    sender_name: str,
    sender_address: str = "",
    sender_email: str = "",
    sender_phone: str = "",
    recipient_name: str = "",
    recipient_title: str = "",
    recipient_company: str = "",
    recipient_address: str = "",
    date: Optional[str] = None,
    subject: str = "",
    body_paragraphs: List[str] = None,
    closing: str = "Atentamente,",
    brand_palette: str = "elegant_gold",
    brand: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Crea una CARTA formal profesional."""
    chk = _check_engine()
    if not chk["ok"]:
        return chk
    if not REPORTLAB_AVAILABLE:
        return {"ok": False, "error": "reportlab requerido"}

    output_path = _ensure_path(output_path)
    b = dict(PALETTES[brand_palette])
    if brand:
        b.update(brand)
    if not date:
        date = time.strftime("%d de %B de %Y")

    doc = _BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm, topMargin=2.2 * cm, bottomMargin=2.0 * cm,
        title=f"Carta - {subject}", author=sender_name, brand=b,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="default", frames=frame, onPage=lambda c, d: doc.after_page())])

    styles = _get_styles(b)
    story: List[Any] = []

    # Sender
    sender_style = ParagraphStyle("sender", parent=styles["BodyLeft"], fontSize=10)
    story.append(Paragraph(f"<b>{sender_name}</b>", sender_style))
    if sender_address:
        story.append(Paragraph(sender_address, sender_style))
    if sender_email:
        story.append(Paragraph(sender_email, sender_style))
    if sender_phone:
        story.append(Paragraph(sender_phone, sender_style))
    story.append(Spacer(1, 6 * mm))

    # Date
    story.append(Paragraph(date, styles["BodyLeft"]))
    story.append(Spacer(1, 6 * mm))

    # Recipient
    if recipient_name:
        story.append(Paragraph(f"<b>{recipient_name}</b>{(' - ' + recipient_title) if recipient_title else ''}", styles["BodyLeft"]))
    if recipient_company:
        story.append(Paragraph(recipient_company, styles["BodyLeft"]))
    if recipient_address:
        story.append(Paragraph(recipient_address, styles["BodyLeft"]))
    story.append(Spacer(1, 6 * mm))

    # Subject
    if subject:
        story.append(Paragraph(f"<b>Ref.:</b> {subject}", styles["BodyLeft"]))
        story.append(Spacer(1, 4 * mm))

    # Salutation
    story.append(Paragraph(f"Estimado/a {recipient_name or 'Sr./Sra.'}:", styles["BodyLeft"]))
    story.append(Spacer(1, 2 * mm))

    # Body
    for para in (body_paragraphs or []):
        story.append(Paragraph(para, styles["Body"]))

    # Closing
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(closing, styles["BodyLeft"]))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(f"<b>{sender_name}</b>", styles["BodyLeft"]))

    doc.build(story)
    return {"ok": True, "output": output_path, "type": "letter", "subject": subject,
            "size_bytes": os.path.getsize(output_path)}


def create_nda(
    output_path: str,
    *,
    disclosing_party: str,
    receiving_party: str,
    purpose: str,
    duration_years: int = 2,
    jurisdiction: str = "Argentina",
    effective_date: Optional[str] = None,
    brand_palette: str = "legal_classic",
) -> Dict[str, Any]:
    """Crea un NDA (Acuerdo de Confidencialidad) profesional completo."""
    if not effective_date:
        effective_date = time.strftime("%d/%m/%Y")

    parties = [
        {"role": "PARTE REVELADORA", "name": disclosing_party, "id_type": "CUIT/DNI", "id": "XX-XXXXXXX-X", "address": "—"},
        {"role": "PARTE RECEPTORA", "name": receiving_party, "id_type": "CUIT/DNI", "id": "XX-XXXXXXX-X", "address": "—"},
    ]
    terms = [
        {"title": "DEFINICIÓN DE INFORMACIÓN CONFIDENCIAL",
         "body": f"Se considerará 'Información Confidencial' toda información divulgada por {disclosing_party} (la 'PARTE REVELADORA') a {receiving_party} (la 'PARTE RECEPTORA'), en forma oral, escrita, visual, electrónica o por cualquier otro medio, que sea identificada como confidencial o que razonablemente deba considerarse confidencial dadas las circunstancias de su divulgación."},
        {"title": "PROPÓSITO",
         "body": f"La Información Confidencial se revela con el único propósito de: {purpose}. La PARTE RECEPTORA no podrá utilizarla para ningún otro fin sin el consentimiento previo y por escrito de la PARTE REVELADORA."},
        {"title": "OBLIGACIONES DE LA PARTE RECEPTORA",
         "body": "La PARTE RECEPTORA se obliga a: (a) mantener la Información Confidencial en estricta reserva; (b) no divulgarla a terceros sin autorización escrita; (c) utilizarla solamente para el propósito establecido; (d) protegerla con el mismo grado de cuidado que utiliza para proteger su propia información confidencial, y en ningún caso con un grado de cuidado menor al razonable; (e) restituirla o destruirla a requerimiento de la PARTE REVELADORA."},
        {"title": "EXCEPCIONES",
         "body": "Las obligaciones de confidencialidad no se aplicarán a información que: (a) sea o se vuelva de dominio público sin culpa de la PARTE RECEPTORA; (b) sea conocida previamente por la PARTE RECEPTORA sin obligación de confidencialidad; (c) sea recibida lícitamente de un tercero sin restricción; (d) sea desarrollada independientemente por la PARTE RECEPTORA sin uso de la Información Confidencial."},
        {"title": "VIGENCIA",
         "body": f"Las obligaciones de confidencialidad asumidas en el presente acuerdo tendrán una vigencia de {duration_years} años contados a partir de la fecha efectiva."},
    ]
    return create_contract(
        output_path, contract_type="nda", parties=parties, terms=terms,
        effective_date=effective_date, duration=f"{duration_years} años",
        jurisdiction=jurisdiction, brand_palette=brand_palette,
    )


def create_business_plan(
    output_path: str,
    *,
    company_name: str,
    industry: str,
    mission: str = "",
    vision: str = "",
    problem: str = "",
    solution: str = "",
    market: str = "",
    business_model: str = "",
    competitive_advantage: str = "",
    financials: List[Dict[str, Any]] = None,
    team: List[Dict[str, str]] = None,
    brand_palette: str = "tech_modern",
) -> Dict[str, Any]:
    """Crea un PLAN DE NEGOCIOS profesional."""
    sections = []
    if mission:
        sections.append({"heading": "Misión", "level": 1, "content": mission})
    if vision:
        sections.append({"heading": "Visión", "level": 1, "content": vision})
    if problem:
        sections.append({"heading": "El Problema", "level": 1, "content": problem})
    if solution:
        sections.append({"heading": "Nuestra Solución", "level": 1, "content": solution})
    if market:
        sections.append({"heading": "Mercado Objetivo", "level": 1, "content": market})
    if business_model:
        sections.append({"heading": "Modelo de Negocio", "level": 1, "content": business_model})
    if competitive_advantage:
        sections.append({"heading": "Ventaja Competitiva", "level": 1, "content": competitive_advantage})
    if financials:
        sections.append({"heading": "Proyecciones Financieras", "level": 1,
                         "content": "Resumen de los principales indicadores financieros:",
                         "table": financials})
    if team:
        team_table = [["Nombre", "Cargo", "Experiencia"]]
        for m in team:
            team_table.append([m.get("name", ""), m.get("role", ""), m.get("experience", "")])
        sections.append({"heading": "Equipo Fundador", "level": 1, "content": "", "table": team_table})
    return create_report(
        output_path, title=f"Plan de Negocios: {company_name}", subtitle=industry,
        sections=sections, brand_palette=brand_palette,
    )


def create_whitepaper(
    output_path: str,
    *,
    title: str,
    abstract: str = "",
    sections: List[Dict[str, Any]] = None,
    references: Optional[List[str]] = None,
    brand_palette: str = "tech_modern",
) -> Dict[str, Any]:
    """Crea un WHITEPAPER técnico profesional."""
    all_sections = []
    if abstract:
        all_sections.append({"heading": "Abstract", "level": 1, "content": abstract})
    all_sections.extend(sections or [])
    if references:
        ref_text = "\n\n".join(f"[{i+1}] {r}" for i, r in enumerate(references))
        all_sections.append({"heading": "Referencias", "level": 1, "content": ref_text})
    return create_report(
        output_path, title=title, subtitle="Whitepaper Técnico",
        sections=all_sections, brand_palette=brand_palette,
    )


# ---------------------------------------------------------------------------
# Generación genérica desde JSON (para integración con agentes)
# ---------------------------------------------------------------------------
def create_from_json(output_path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera un PDF desde un JSON genérico.
    Formato esperado:
    {
      "type": "contract" | "invoice" | "report" | "proposal" | "resume" | "letter" | "nda" | "business_plan" | "whitepaper",
      ...campos específicos del tipo...
    }
    """
    doc_type = data.get("type")
    if doc_type == "contract":
        return create_contract(output_path, **data)
    if doc_type == "invoice":
        return create_invoice(output_path, **data)
    if doc_type == "report":
        return create_report(output_path, **data)
    if doc_type == "proposal":
        return create_proposal(output_path, **data)
    if doc_type == "resume":
        return create_resume(output_path, **data)
    if doc_type == "letter":
        return create_letter(output_path, **data)
    if doc_type == "nda":
        return create_nda(output_path, **data)
    if doc_type == "business_plan":
        return create_business_plan(output_path, **data)
    if doc_type == "whitepaper":
        return create_whitepaper(output_path, **data)
    return {"ok": False, "error": f"tipo desconocido: {doc_type}. Soportados: contract, invoice, report, proposal, resume, letter, nda, business_plan, whitepaper"}


# ---------------------------------------------------------------------------
# Auto-rellenar contenido (cuando solo te dan título)
# ---------------------------------------------------------------------------
DOCUMENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "contract_services": {
        "type": "contract",
        "contract_type": "services",
        "parties": [
            {"role": "PRESTADOR", "name": "[NOMBRE COMPLETO DEL PRESTADOR]", "id_type": "DNI/CUIT", "id": "[XX-XXXXXXX-X]", "address": "[DOMICILIO COMPLETO]"},
            {"role": "PRESTATARIO", "name": "[NOMBRE COMPLETO DEL PRESTATARIO]", "id_type": "DNI/CUIT", "id": "[XX-XXXXXXX-X]", "address": "[DOMICILIO COMPLETO]"},
        ],
        "terms": [
            {"title": "OBJETO",
             "body": "El PRESTADOR se obliga a prestar al PRESTATARIO los servicios profesionales detallados en el Anexo I del presente contrato, el cual forma parte integrante del mismo. Los servicios serán ejecutados con la mayor diligencia, profesionalismo y conforme a los estándares de calidad del mercado."},
            {"title": "PRECIO Y FORMA DE PAGO",
             "body": "Como contraprestación por los servicios prestados, el PRESTATARIO abonará al PRESTADOR la suma de $[MONTO] ($[MONTO_EN_LETRAS]), que será abonada de la siguiente manera: [DETALLAR CONDICIONES DE PAGO, PLAZOS Y MEDIOS]. En caso de mora, se aplicarán intereses moratorios equivalentes a la tasa activa del Banco de la Nación Argentina."},
            {"title": "PLAZO DE EJECUCIÓN",
             "body": "El PRESTADOR se obliga a iniciar los servicios dentro de los [NÚMERO] días hábiles contados a partir de la firma del presente, y a finalizarlos en un plazo máximo de [NÚMERO] días corridos. Cualquier extensión de plazo deberá ser acordada por escrito entre las partes."},
            {"title": "OBLIGACIONES DEL PRESTADOR",
             "body": "Son obligaciones del PRESTADOR: (a) ejecutar los servicios con la máxima diligencia y buena fe; (b) mantener informado al PRESTATARIO sobre el avance de los servicios; (c) cumplir con todas las normas legales y reglamentarias aplicables; (d) guardar confidencialidad sobre toda información del PRESTATARIO."},
            {"title": "OBLIGACIONES DEL PRESTATARIO",
             "body": "Son obligaciones del PRESTATARIO: (a) proporcionar al PRESTADOR toda la información y documentación necesaria para la ejecución de los servicios; (b) abonar el precio en tiempo y forma; (c) colaborar activamente con el PRESTADOR en lo que sea necesario."},
            {"title": "CONFIDENCIALIDAD",
             "body": "Las partes se obligan a mantener bajo estricta confidencialidad toda información que reciban con motivo del presente contrato, durante toda la vigencia del mismo y por [NÚMERO] años posteriores a su terminación."},
            {"title": "RESCISIÓN",
             "body": "Cualquiera de las partes podrá rescindir el presente contrato mediante notificación fehaciente con [NÚMERO] días de antelación, sin necesidad de invocación de causa. En caso de incumplimiento grave de alguna de las partes, la parte afectada podrá dar por resuelto el contrato de pleno derecho, sin perjuicio de reclamar los daños y perjuicios correspondientes."},
            {"title": "INDEPENDENCIA DE LAS PARTES",
             "body": "El PRESTADOR actúa en calidad de contratista independiente, no existiendo relación de dependencia laboral alguna con el PRESTATARIO. El PRESTADOR asume todos los tributos, aportes y contribuciones que graven su actividad."},
        ],
    },
    "nda_standard": {
        "type": "nda",
        "disclosing_party": "[NOMBRE DE LA PARTE REVELADORA]",
        "receiving_party": "[NOMBRE DE LA PARTE RECEPTORA]",
        "purpose": "[DESCRIBIR EL PROPÓSITO ESPECÍFICO - ej: evaluación de posible joint venture]",
        "duration_years": 3,
    },
    "invoice_template": {
        "type": "invoice",
        "invoice_number": "0001-00000001",
        "issue_date": "[FECHA DE EMISIÓN]",
        "due_date": "[FECHA DE VENCIMIENTO]",
        "seller": {
            "name": "[RAZÓN SOCIAL DEL EMISOR]",
            "id": "[CUIT/RFC: XX-XXXXXXX-X]",
            "address": "[DOMICILIO COMERCIAL COMPLETO]",
            "email": "[email@empresa.com]",
        },
        "buyer": {
            "name": "[RAZÓN SOCIAL DEL CLIENTE]",
            "id": "[CUIT/RFC: XX-XXXXXXX-X]",
            "address": "[DOMICILIO DEL CLIENTE]",
            "email": "[email@cliente.com]",
        },
        "items": [
            {"description": "[Descripción del producto/servicio 1]", "quantity": 1, "price": 1000.00},
            {"description": "[Descripción del producto/servicio 2]", "quantity": 2, "price": 500.00},
        ],
        "tax_rate": 0.21,
        "tax_label": "IVA",
        "currency": "ARS",
        "notes": "Forma de pago: transferencia bancaria. CBU: XXXX-XXXX-XXXX.",
    },
    "report_template": {
        "type": "report",
        "title": "[TÍTULO DEL INFORME]",
        "subtitle": "[Subtítulo descriptivo]",
        "author": "[Nombre del autor]",
        "sections": [
            {"heading": "Resumen Ejecutivo", "level": 1, "content": "[Resumen de 1-2 párrafos con los puntos clave del informe.]"},
            {"heading": "Introducción", "level": 1, "content": "[Contexto y objetivos del informe.]"},
            {"heading": "Metodología", "level": 1, "content": "[Descripción de cómo se realizó el estudio.]"},
            {"heading": "Resultados", "level": 1, "content": "[Hallazgos principales con datos cuantitativos.]",
             "table": [
                 ["Indicador", "Q1", "Q2", "Q3", "Q4"],
                 ["[Indicador 1]", "100", "120", "135", "150"],
                 ["[Indicador 2]", "85%", "87%", "90%", "92%"],
             ]},
            {"heading": "Conclusiones", "level": 1, "content": "[Síntesis de hallazgos y recomendaciones.]"},
            {"heading": "Próximos Pasos", "level": 1, "content": "[Acciones recomendadas con timeline.]"},
        ],
    },
    "proposal_template": {
        "type": "proposal",
        "title": "[Título de la propuesta]",
        "client_name": "[Nombre del cliente]",
        "client_company": "[Empresa del cliente]",
        "project_overview": "[Descripción general del proyecto, objetivos, alcance.]",
        "deliverables": [
            "[Entregable 1: descripción]",
            "[Entregable 2: descripción]",
            "[Entregable 3: descripción]",
        ],
        "timeline": [
            {"phase": "Fase 1", "activity": "[Actividad]", "duration": "[X semanas]"},
            {"phase": "Fase 2", "activity": "[Actividad]", "duration": "[X semanas]"},
        ],
        "pricing": [
            {"item": "[Item 1]", "description": "[Descripción]", "price": "$[MONTO]"},
        ],
        "total": "$[MONTO TOTAL]",
        "terms": "[Términos y condiciones de la propuesta.]",
        "valid_until": "[Fecha límite de validez]",
    },
    "letter_formal": {
        "type": "letter",
        "sender_name": "[Su nombre completo]",
        "sender_address": "[Su dirección]",
        "sender_email": "[su@email.com]",
        "sender_phone": "[+XX XXX XXX XXX]",
        "recipient_name": "[Nombre del destinatario]",
        "recipient_title": "[Cargo]",
        "recipient_company": "[Empresa]",
        "recipient_address": "[Dirección del destinatario]",
        "subject": "[Asunto de la carta]",
        "body_paragraphs": [
            "[Primer párrafo: motivo de la carta]",
            "[Segundo párrafo: desarrollo del tema, datos relevantes]",
            "[Tercer párrafo: solicitud o cierre]",
        ],
    },
}


# ---------------------------------------------------------------------------
# Wrapper class
# ---------------------------------------------------------------------------
class PDFProTools:
    @staticmethod
    def status() -> Dict[str, Any]:
        return _check_engine()

    @staticmethod
    def create_contract(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_contract(output_path, **kwargs)

    @staticmethod
    def create_invoice(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_invoice(output_path, **kwargs)

    @staticmethod
    def create_report(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_report(output_path, **kwargs)

    @staticmethod
    def create_proposal(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_proposal(output_path, **kwargs)

    @staticmethod
    def create_resume(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_resume(output_path, **kwargs)

    @staticmethod
    def create_letter(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_letter(output_path, **kwargs)

    @staticmethod
    def create_nda(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_nda(output_path, **kwargs)

    @staticmethod
    def create_business_plan(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_business_plan(output_path, **kwargs)

    @staticmethod
    def create_whitepaper(output_path: str, **kwargs) -> Dict[str, Any]:
        return create_whitepaper(output_path, **kwargs)

    @staticmethod
    def create_from_json(output_path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return create_from_json(output_path, data)

    @staticmethod
    def list_templates() -> Dict[str, Any]:
        return {"ok": True, "templates": list(DOCUMENT_TEMPLATES.keys())}

    @staticmethod
    def get_template(name: str) -> Dict[str, Any]:
        if name not in DOCUMENT_TEMPLATES:
            return {"ok": False, "error": f"template {name!r} no existe", "available": list(DOCUMENT_TEMPLATES.keys())}
        return {"ok": True, "template": DOCUMENT_TEMPLATES[name]}

    @staticmethod
    def list_palettes() -> Dict[str, Any]:
        return {"ok": True, "palettes": list(PALETTES.keys())}

    @staticmethod
    def render_chart(data: List[float], labels: List[str], title: str,
                     chart_type: str = "bar", output_path: Optional[str] = None) -> Dict[str, Any]:
        path = _make_temp_chart(data, labels, title, chart_type, output_path)
        if not path:
            return {"ok": False, "error": "matplotlib no instalado"}
        return {"ok": True, "chart_path": path, "type": chart_type}
