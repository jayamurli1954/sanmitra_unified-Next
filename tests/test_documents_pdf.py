"""Shared document renderer: font registration, ₹ glyph, and bilingual runs.

The bundled Noto fonts are script-only (no Latin), so multilingual documents use
per-run fonts: Latin/English in a core font, local script + ₹ in a Noto font.
These tests confirm the fonts register and that the right font is embedded when a
document uses ₹ or a local-language run.
"""
from __future__ import annotations

from app.core.documents import (
    DocumentColumn,
    DocumentLine,
    DocumentParty,
    DocumentSpec,
    LocalText,
    render_document_pdf,
)
from app.core.documents import fonts


def _spec(lines, *, language=None, totals=None) -> DocumentSpec:
    return DocumentSpec(
        title="Receipt",
        number="R-1",
        seller=DocumentParty(name="Temple Trust"),
        buyer=DocumentParty(name="Devotee"),
        columns=[DocumentColumn("a", "Item", "left", 3.0), DocumentColumn("b", "Amount", "right", 1.0)],
        lines=lines,
        totals=totals or [],
        language=language,
    )


def test_fonts_register_expected_scripts():
    registered = fonts.register_document_fonts()
    assert "NotoSansKannada" in registered
    assert "NotoSansTamil" in registered
    assert fonts.font_for_language("kannada") == "NotoSansKannada"
    assert fonts.font_for_language("hindi") == "NotoSansDevanagari"  # Devanagari script
    assert fonts.font_for_language("klingon") is None
    assert fonts.font_for_language(None) is None
    assert fonts.rupee_font_name() is not None


def test_rupee_uses_a_noto_font_in_output():
    # ₹ is absent from the core fonts, so the renderer must embed a Noto font.
    spec = _spec([DocumentLine({"a": "Donation", "b": "₹1,000.00"})])
    pdf = render_document_pdf(spec)
    assert pdf.startswith(b"%PDF")
    assert b"NotoSans" in pdf  # a glyph-bearing font was embedded for ₹


def test_bilingual_local_text_embeds_script_font():
    # A Kannada run must pull in the Kannada font specifically.
    line = DocumentLine({"a": LocalText("ದೇಣಿಗೆ", language="kannada"), "b": "₹500.00"})
    pdf = render_document_pdf(_spec([line], language="kannada"))
    assert pdf.startswith(b"%PDF")
    assert b"Kannada" in pdf


def test_mixed_english_and_local_runs_render():
    # A list mixes an English run with a Kannada run in one cell.
    cell = ["Donation / ", LocalText("ದೇಣಿಗೆ", language="kannada")]
    line = DocumentLine({"a": cell, "b": "₹750.00"})
    pdf = render_document_pdf(_spec([line], language="kannada"))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_english_only_document_still_renders():
    pdf = render_document_pdf(_spec([DocumentLine({"a": "Consulting", "b": "₹10,000.00"})]))
    assert pdf.startswith(b"%PDF")
