"""Build Jinja2 context for MandirMitra HTML Panchang cards.

Reuses i18n tables from scripts/panchang_infographic (synced from WhatsApp message maps).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.panchang_infographic.render import (
    TriText,
    _lookup,
    _samvatsara_name,
    _translate_masa,
    _translate_tithi,
    load_i18n,
    time_range,
)

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]
FONT_DIR = REPO_ROOT / "app" / "core" / "documents" / "fonts"
LOGO_DIR = PACKAGE_DIR / "logos"
ART_DIR = PACKAGE_DIR / "artwork"

# Canonical Kannada for Purnima (matches MandirMitra festival copy).
_PURNIMA_KN_CANON = "ಪೌರ್ಣಿಮಾ"
_PURNIMA_KN_ALT = "ಪೂರ್ಣಿಮಾ"


def _path_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _prefer_asset(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.is_file():
            return path
    return None


def _normalize_kn(text: str) -> str:
    """Keep ಪೌರ್ಣಿಮಾ spelling consistent across tithi and vishesha."""
    return text.replace(_PURNIMA_KN_ALT, _PURNIMA_KN_CANON)


def build_card_context(data: dict[str, Any], *, i18n_path: Path | None = None) -> dict[str, Any]:
    """Map PanchangService payload → flat template variables."""
    i18n = load_i18n(i18n_path)
    gregorian = data.get("date", {}).get("gregorian", {}) or {}
    hindu = data.get("date", {}).get("hindu", {}) or {}
    location = data.get("location", {}) or {}
    panchang = data.get("panchang", {}) or {}
    tithi = panchang.get("tithi", {}) or {}
    nakshatra = panchang.get("nakshatra", {}) or {}
    yoga = panchang.get("yoga", {}) or {}
    karana = panchang.get("karana", {}) or {}
    vara = panchang.get("vara", {}) or {}
    kaala = data.get("inauspicious_times") or data.get("kaala") or {}
    good = data.get("auspicious_times") or data.get("muhurat") or {}
    extra_bad = data.get("additional_inauspicious_times") or {}

    ayana_name = (
        data.get("ayana")
        if isinstance(data.get("ayana"), str)
        else (data.get("ayana") or {}).get("name", "")
    )
    vara_name = vara.get("name") or gregorian.get("day") or gregorian.get("day_of_week") or ""
    karana_name = karana.get("current") or karana.get("name") or ""

    samvatsara = _lookup("samvatsara", _samvatsara_name(data), i18n)
    ayana = _lookup("ayana", str(ayana_name), i18n)
    masa = _translate_masa(str(hindu.get("month") or ""), i18n)
    vara_tri = _lookup("vara", str(vara_name), i18n)
    if vara.get("sanskrit"):
        vara_tri = TriText(vara_tri.en, vara_tri.kn, str(vara["sanskrit"]))
    tithi_tri = _translate_tithi(
        str(tithi.get("name") or ""),
        str(tithi.get("paksha") or hindu.get("paksha") or ""),
        i18n,
    )
    nakshatra_tri = _lookup("nakshatra", str(nakshatra.get("name") or ""), i18n)
    yoga_tri = _lookup("yoga", str(yoga.get("name") or ""), i18n)
    karana_tri = _lookup("karana", str(karana_name), i18n)

    date_label = gregorian.get("formatted") or gregorian.get("date") or "Today"
    city = location.get("city") or "Temple"
    date_iso = str(gregorian.get("date") or "").replace("-", "_") or "today"

    vishesha: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in data.get("south_india_special") or []:
        if not isinstance(item, dict):
            continue
        en = str(item.get("english") or "").strip()
        kn = str(item.get("kannada") or "").strip()
        hi = str(item.get("sanskrit") or "").strip()
        if not en and item.get("text"):
            en = str(item["text"])
        key = en.lower()
        if not en or key in seen:
            continue
        seen.add(key)
        vishesha.append({"en": en, "kn": _normalize_kn(kn), "hi": hi})

    rows = [
        {"label": "Samvatsara", "en": samvatsara.en, "kn": _normalize_kn(samvatsara.kn), "hi": samvatsara.hi, "icon": "🪔"},
        {"label": "Ayana", "en": ayana.en, "kn": _normalize_kn(ayana.kn), "hi": ayana.hi, "icon": "☀️"},
        {"label": "Masa", "en": masa.en, "kn": _normalize_kn(masa.kn), "hi": masa.hi, "icon": "🌙"},
        {"label": "Vara", "en": vara_tri.en, "kn": _normalize_kn(vara_tri.kn), "hi": vara_tri.hi, "icon": "📅"},
        {"label": "Tithi", "en": tithi_tri.en, "kn": _normalize_kn(tithi_tri.kn), "hi": tithi_tri.hi, "icon": "🌕"},
        {"label": "Nakshatra", "en": nakshatra_tri.en, "kn": _normalize_kn(nakshatra_tri.kn), "hi": nakshatra_tri.hi, "icon": "⭐"},
        {"label": "Yoga", "en": yoga_tri.en, "kn": _normalize_kn(yoga_tri.kn), "hi": yoga_tri.hi, "icon": "🪷"},
        {"label": "Karana", "en": karana_tri.en, "kn": _normalize_kn(karana_tri.kn), "hi": karana_tri.hi, "icon": "🐚"},
    ]

    inauspicious = [
        {"label": "Rahu Kala", "value": time_range(kaala.get("rahu_kaal") or kaala.get("rahu"))},
        {"label": "Yamaganda", "value": time_range(kaala.get("yamaganda"))},
        {"label": "Gulika Kala", "value": time_range(kaala.get("gulika"))},
        {"label": "Dur Muhurta", "value": time_range(extra_bad.get("dur_muhurta"))},
        {"label": "Varjyam", "value": time_range(extra_bad.get("varjyam"))},
    ]
    auspicious = [
        {"label": "Abhijit", "value": time_range(good.get("abhijit_muhurat") or good.get("abhijit"))},
        {"label": "Brahma Muhurat", "value": time_range(good.get("brahma_muhurat") or good.get("brahma"))},
        {"label": "Amrita Kalam", "value": time_range(good.get("amrita_kalam") or kaala.get("amrita"))},
    ]

    kn_font = FONT_DIR / "NotoSansKannada-Regular.ttf"
    hi_font = FONT_DIR / "NotoSansDevanagari-Regular.ttf"
    logo_mm = _prefer_asset(LOGO_DIR / "mandirmitra.png", LOGO_DIR / "mandirmitra.svg")
    logo_sm = _prefer_asset(LOGO_DIR / "sanmitra.png", LOGO_DIR / "sanmitra.svg")
    art_diya = _prefer_asset(ART_DIR / "diya.png")
    art_moon = _prefer_asset(ART_DIR / "moon.png")
    frame_svg = _prefer_asset(ART_DIR / "frame.svg")

    return {
        "title_en": "Today's Panchang",
        "title_kn": "ಇಂದಿನ ಪಂಚಾಂಗ",
        "city": city,
        "date_label": date_label,
        "date_iso": date_iso,
        "location_date": f"{city} · {date_label}",
        "rows": rows,
        "inauspicious": [row for row in inauspicious if row["value"] and row["value"] != "—"],
        "auspicious": [row for row in auspicious if row["value"] and row["value"] != "—"],
        "vishesha": vishesha[:3],
        "footer_brand": "Generated by MandirMitra · SanMitra Tech",
        "footer_disclaimer": "For guidance only — confirm with temple tradition before muhurta use.",
        "font_kannada_uri": _path_uri(kn_font) if kn_font.is_file() else "",
        "font_hindi_uri": _path_uri(hi_font) if hi_font.is_file() else "",
        "logo_mandirmitra_uri": _path_uri(logo_mm) if logo_mm else "",
        "logo_sanmitra_uri": _path_uri(logo_sm) if logo_sm else "",
        "art_diya_uri": _path_uri(art_diya) if art_diya else "",
        "art_moon_uri": _path_uri(art_moon) if art_moon else "",
        "frame_svg_uri": _path_uri(frame_svg) if frame_svg else "",
        "css_uri": _path_uri(PACKAGE_DIR / "style.css"),
    }
