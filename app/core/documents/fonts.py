"""Font registration for the shared document renderer.

The bundled Noto fonts are *script-only*: each contains its Indian script plus
digits, punctuation and the ₹ glyph — but **no Latin letters**. So multilingual
documents can't use one universal font; instead Latin/English text renders in a
core font (Helvetica) and local-script runs render in the matching Noto font.
This module registers the Noto fonts and exposes lookups the renderer uses to
pick a font per text run.

Fonts are bundled under ``app/core/documents/fonts``; system font dirs are also
searched so a Render/Linux host's Noto install works as a fallback.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_logger = logging.getLogger(__name__)

_BUNDLED_DIR = Path(__file__).resolve().parent / "fonts"
_SYSTEM_DIRS = (
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/opentype/noto",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/app/fonts",
)

# language -> (registered font name, font file)
_LANGUAGE_FONTS: dict[str, tuple[str, str]] = {
    "hindi": ("NotoSansDevanagari", "NotoSansDevanagari-Regular.ttf"),
    "marathi": ("NotoSansDevanagari", "NotoSansDevanagari-Regular.ttf"),
    "sanskrit": ("NotoSansDevanagari", "NotoSansDevanagari-Regular.ttf"),
    "kannada": ("NotoSansKannada", "NotoSansKannada-Regular.ttf"),
    "tamil": ("NotoSansTamil", "NotoSansTamil-Regular.ttf"),
    "telugu": ("NotoSansTelugu", "NotoSansTelugu-Regular.ttf"),
    "malayalam": ("NotoSansMalayalam", "NotoSansMalayalam-Regular.ttf"),
}

LANGUAGES = frozenset(_LANGUAGE_FONTS)

_registered: dict[str, str] = {}  # font_name -> resolved path (registered this process)
_done = False


def _find_font_file(filename: str) -> str | None:
    bundled = _BUNDLED_DIR / filename
    if bundled.is_file():
        return str(bundled)
    for directory in _SYSTEM_DIRS:
        candidate = os.path.join(directory, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def register_document_fonts() -> dict[str, str]:
    """Register all available Noto fonts with reportlab (idempotent).

    Returns the map of registered font name -> file path. Missing fonts are
    skipped silently so rendering degrades to Latin-only rather than failing.
    """
    global _done
    if _done:
        return dict(_registered)
    seen: set[str] = set()
    for font_name, filename in _LANGUAGE_FONTS.values():
        if font_name in seen:
            continue
        seen.add(font_name)
        path = _find_font_file(filename)
        if not path:
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, path))
            _registered[font_name] = path
        except Exception as exc:  # pragma: no cover - font load is environment-dependent
            _logger.warning("Could not register font %s from %s: %s", font_name, path, exc)
    _done = True
    return dict(_registered)


def font_for_language(language: str | None) -> str | None:
    """Registered font name for a language's script, or None if unavailable."""
    if not language:
        return None
    entry = _LANGUAGE_FONTS.get(str(language).strip().lower())
    if not entry:
        return None
    register_document_fonts()
    name = entry[0]
    return name if name in _registered else None


def rupee_font_name() -> str | None:
    """A registered font that contains the ₹ glyph (the core fonts do not).

    Any of the bundled Noto fonts carries ₹, so the first registered one wins.
    Returns None when no Noto font is available (caller should fall back to a
    plain "Rs." prefix)."""
    register_document_fonts()
    return next(iter(_registered), None)
