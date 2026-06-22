"""Reportlab renderer for the shared ``DocumentSpec``.

Uses platypus (flowables) so long line-item tables paginate automatically. The
renderer is intentionally domain-agnostic: it draws whatever columns, totals and
text the caller put in the spec. Money formatting, GST logic, and currency
symbols are the mapper's responsibility — we only place strings.

Core fonts (Helvetica) are used to avoid bundling a TTF; callers should prefer an
ASCII currency prefix such as "Rs." over the ₹ glyph, which Helvetica cannot
render.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.documents.fonts import font_for_language, register_document_fonts, rupee_font_name
from app.core.documents.spec import DocumentSpec, LocalText

# Register the bundled Noto fonts once at import so per-run lookups are cheap.
register_document_fonts()

_PAGE_SIZES = {"A4": A4, "A5": A5}
_RUPEE = "₹"

_BODY = ParagraphStyle("doc-body", fontName="Helvetica", fontSize=8.5, leading=11)
_BODY_RIGHT = ParagraphStyle("doc-body-r", parent=_BODY, alignment=2)
_SMALL = ParagraphStyle("doc-small", fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#555555"))
_LABEL = ParagraphStyle("doc-label", fontName="Helvetica-Bold", fontSize=8.5, leading=11)


def _esc(value) -> str:
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _wrap_rupee(escaped: str) -> str:
    """Render any ₹ in a font that has the glyph (core fonts lack it).

    When no Noto font is registered, fall back to the ASCII 'Rs.' so the symbol
    never shows as a missing-glyph box."""
    if _RUPEE not in escaped:
        return escaped
    rupee_font = rupee_font_name()
    if rupee_font:
        return escaped.replace(_RUPEE, f'<font name="{rupee_font}">{_RUPEE}</font>')
    return escaped.replace(_RUPEE, "Rs.")


def _rich(value, default_language: str | None = None) -> str:
    """Turn a str / LocalText / mixed list into reportlab inline markup.

    Plain strings render in the paragraph's base (Latin) font with ₹ wrapped;
    LocalText runs render in the matching Indian-script font. This is what lets a
    single line mix English and, say, Kannada correctly — the bundled Noto fonts
    are script-only and cannot render Latin themselves."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "".join(_rich(part, default_language) for part in value)
    if isinstance(value, LocalText):
        inner = _esc(value.text)
        font = font_for_language(value.language or default_language)
        if font:
            return f'<font name="{font}">{inner}</font>'
        # No script font available — still show the text (may miss glyphs).
        return _wrap_rupee(inner)
    return _wrap_rupee(_esc(value))


def _party_block(party, *, heading: str | None = None) -> list:
    bits = []
    if heading:
        bits.append(f'<font name="Helvetica-Bold">{_esc(heading)}</font><br/>')
    bits.append(f'<font name="Helvetica-Bold">{_esc(party.name)}</font>')
    for line in party.address_lines:
        if str(line or "").strip():
            bits.append(f"<br/>{_esc(line)}")
    if party.gstin:
        bits.append(f"<br/>GSTIN: {_esc(party.gstin)}")
    return Paragraph("".join(bits), _BODY)


def _header_table(spec: DocumentSpec, width: float) -> Table:
    left = _party_block(spec.seller)
    meta_bits = [f'<font name="Helvetica-Bold" size="13">{_rich(spec.title, spec.language)}</font>']
    meta_bits.append(f"<br/>No: {_esc(spec.number)}")
    for label, value in spec.meta:
        meta_bits.append(f"<br/>{_esc(label)}: {_rich(value, spec.language)}")
    right = Paragraph("".join(meta_bits), _BODY_RIGHT)
    table = Table([[left, right]], colWidths=[width * 0.55, width * 0.45])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _line_items_table(spec: DocumentSpec, width: float) -> Table:
    align_map = {"left": "LEFT", "right": "RIGHT", "center": "CENTER"}
    total_weight = sum(max(c.weight, 0.01) for c in spec.columns) or 1.0
    col_widths = [width * (c.weight / total_weight) for c in spec.columns]

    header = [Paragraph(f'<font name="Helvetica-Bold">{_esc(c.label)}</font>', _SMALL) for c in spec.columns]
    body = [header]
    for line in spec.lines:
        body.append([Paragraph(_rich(line.cells.get(c.key, ""), spec.language), _SMALL) for c in spec.columns])

    table = Table(body, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
    ]
    for idx, col in enumerate(spec.columns):
        style.append(("ALIGN", (idx, 0), (idx, -1), align_map.get(col.align, "LEFT")))
    table.setStyle(TableStyle(style))
    return table


def _totals_table(spec: DocumentSpec, width: float) -> Table:
    rows = []
    for total in spec.totals:
        label_style = _LABEL if total.emphasize else _BODY
        value_style = ParagraphStyle("tv", parent=_BODY_RIGHT, fontName="Helvetica-Bold" if total.emphasize else "Helvetica")
        rows.append([
            Paragraph(_rich(total.label, spec.language), label_style),
            Paragraph(_rich(total.value, spec.language), value_style),
        ])
    inner = Table(rows, colWidths=[width * 0.28, width * 0.17])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for idx, total in enumerate(spec.totals):
        if total.emphasize:
            style.append(("LINEABOVE", (0, idx), (-1, idx), 0.6, colors.HexColor("#1f2d3d")))
    inner.setStyle(TableStyle(style))
    # Right-align the totals block within the page width.
    wrapper = Table([[inner]], colWidths=[width])
    wrapper.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return wrapper


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(doc.pagesize[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_document_pdf(spec: DocumentSpec) -> bytes:
    """Render a ``DocumentSpec`` to PDF bytes."""
    buffer = BytesIO()
    page_size = _PAGE_SIZES.get(spec.page_size, A4)
    margin = 15 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=18 * mm,
        title=f"{spec.title} {spec.number}",
    )
    content_width = page_size[0] - 2 * margin

    story = [
        _header_table(spec, content_width),
        Spacer(1, 8 * mm),
        _party_block(spec.buyer, heading=spec.buyer_heading),
        Spacer(1, 5 * mm),
        _line_items_table(spec, content_width),
        Spacer(1, 3 * mm),
    ]
    if spec.totals:
        story.append(_totals_table(spec, content_width))
        story.append(Spacer(1, 5 * mm))
    if spec.notes:
        story.append(Paragraph(f'<font name="Helvetica-Bold">Notes: </font>{_rich(spec.notes, spec.language)}', _BODY))
        story.append(Spacer(1, 3 * mm))
    if spec.declaration:
        story.append(Paragraph(_rich(spec.declaration, spec.language), _SMALL))
        story.append(Spacer(1, 2 * mm))
    if spec.footer_note:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(_rich(spec.footer_note, spec.language), _SMALL))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()
