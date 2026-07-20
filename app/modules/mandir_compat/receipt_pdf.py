"""MandirMitra donation and seva receipt PDF rendering.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Rendering only; posting and
sequence numbering remain in router.py.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from PIL import Image as PILImage
    from PIL import ImageDraw, ImageFont, features as pil_features
except Exception:
    PILImage = None
    ImageDraw = None
    ImageFont = None
    pil_features = None

try:
    from weasyprint import HTML
except Exception:
    HTML = None

from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.donation_compliance import donation_compliance_receipt_note

MANDIR_COMPAT_DATA_DIR = Path(__file__).resolve().parent / "data"

logger = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    return mandir_router._safe_float(value, default)


def _receipt_number_for_donation(donation: dict[str, Any]) -> str:
    return mandir_router._receipt_number_for_donation(donation)


def _receipt_number_for_seva(doc: dict[str, Any]) -> str:
    return mandir_router._receipt_number_for_seva(doc)


def _generate_donation_receipt_pdf_bytes(
    donation: dict[str, Any],
    *,
    temple_name: str = "Temple",
    temple_profile: dict[str, Any] | None = None,
) -> bytes:
    temple_profile = _build_temple_receipt_profile(temple_profile or {"temple_name": temple_name})
    amount = _safe_float(donation.get("amount"), 0.0)
    devotee = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
    party_source = {
        "devotee_name": donation.get("devotee_name"),
        "name": donation.get("devotee_name") or donation.get("name"),
        "name_prefix": donation.get("devotee_prefix") or donation.get("name_prefix"),
    }
    address_source = {
        "devotee_address": donation.get("devotee_address") or donation.get("address"),
        "city": donation.get("devotee_city") or donation.get("city"),
        "state": donation.get("devotee_state") or donation.get("state"),
        "pincode": donation.get("devotee_pincode") or donation.get("pincode"),
    }
    devotee_name = _compose_receipt_party_name(party_source, devotee, fallback="Unknown Devotee")
    payment_mode = _format_payment_mode_for_receipt(donation.get("payment_mode") or donation.get("payment_method") or "Cash")
    receipt_number = _receipt_number_for_donation(donation)
    donation_date = _format_receipt_date(donation.get("donation_date") or donation.get("created_at"))
    category = str(donation.get("category") or "General Donation").strip() or "General Donation"
    item_parts = [
        str(donation.get("in_kind_item_name") or "").strip(),
        str(donation.get("in_kind_quantity") or "").strip(),
    ]
    item_text = " - ".join(part for part in item_parts if part)
    line_description = category
    if str(donation.get("donation_type") or "").strip().lower() == "in_kind" and item_text:
        line_description = f"{category} ({item_text})"
    devotee_address = _compose_receipt_address_line(address_source, devotee, fallback="--")
    compliance_note = donation_compliance_receipt_note(donation)
    payload = {
        **temple_profile,
        "receipt_title": "Donation Receipt",
        "receipt_title_local": "ದೇಣಿಗೆ ರಶೀದಿ",
        "line_item_header": "Donation Details",
        "line_item_local": "ದೇಣಿಗೆ ವಿವರ",
        "service_date_label": "Donation Date",
        "receipt_number": receipt_number,
        "receipt_date": donation_date,
        "party_name": devotee_name,
        "address_value": devotee_address,
        "amount_words_line": _amount_words_receipt_line(amount, local_language=temple_profile.get("local_language")),
        "payment_line": _receipt_payment_line(
            payment_mode=payment_mode,
            local_language=temple_profile.get("local_language"),
            purpose="donation",
        ),
        "line_items": [{"description": line_description, "amount": amount}],
        "total_amount": amount,
        "include_astro_row": False,
        "include_service_row": False,
        "include_note_row": bool(compliance_note),
        "service_date": donation_date,
        "note_english": compliance_note,
        "system_generated_line": "",
        "powered_by_line": "Powered by Sanmitra Tech Solutions.",
        "local_language": temple_profile.get("local_language"),
        "use_local_labels": True,
    }
    return _build_receipt_pdf_bytes(payload)
def _generate_seva_receipt_pdf_bytes(
    booking: dict[str, Any],
    *,
    temple_name: str = "Temple",
    temple_profile: dict[str, Any] | None = None,
) -> bytes:
    temple_profile = _build_temple_receipt_profile(temple_profile or {"temple_name": temple_name})
    amount = _safe_float(booking.get("amount_paid") or booking.get("amount"), 0.0)
    seva_name = str(booking.get("seva_name") or booking.get("seva") or "Seva Booking").strip() or "Seva Booking"
    use_local_labels = bool(temple_profile.get("local_language"))
    seva_name_local = _as_text(
        booking.get("seva_name_local")
        or booking.get("name_kannada")
        or booking.get("seva_name_kannada"),
        "",
    )
    devotee = booking.get("devotee") if isinstance(booking.get("devotee"), dict) else {}
    party_source = {
        "devotee_name": booking.get("devotee_names") or booking.get("devotee_name"),
        "name": booking.get("devotee_names") or booking.get("devotee_name"),
        "name_prefix": booking.get("devotee_prefix") or booking.get("name_prefix"),
    }
    address_source = {
        "devotee_address": booking.get("devotee_address") or booking.get("address"),
        "city": booking.get("devotee_city") or booking.get("city"),
        "state": booking.get("devotee_state") or booking.get("state"),
        "pincode": booking.get("devotee_pincode") or booking.get("pincode"),
    }
    devotee_name = _compose_receipt_party_name(party_source, devotee, fallback="Devotee")
    booking_date = _format_receipt_date(booking.get("booking_date") or booking.get("created_at"))
    payment_mode = _format_payment_mode_for_receipt(booking.get("payment_mode") or booking.get("payment_method") or "Cash")
    receipt_number = _receipt_number_for_seva(booking)
    devotee_address = _compose_receipt_address_line(address_source, devotee, fallback="--")
    line_items = _extract_seva_line_items(
        booking,
        fallback_name=_compose_receipt_line_description(seva_name, seva_name_local, use_local_labels=use_local_labels),
        fallback_amount=amount,
        use_local_labels=use_local_labels,
    )
    total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)
    if total_amount <= 0:
        total_amount = amount

    payload = {
        **temple_profile,
        "receipt_title": "Seva Receipt",
        "receipt_title_local": "ಸೇವಾ ರಶೀದಿ",
        "receipt_number": receipt_number,
        "receipt_date": booking_date,
        "party_name": devotee_name,
        "address_value": devotee_address,
        "amount_words_line": _amount_words_receipt_line(total_amount, local_language=temple_profile.get("local_language")),
        "payment_line": _receipt_payment_line(
            payment_mode=payment_mode,
            local_language=temple_profile.get("local_language"),
            purpose="seva",
        ),
        "line_items": line_items,
        "total_amount": total_amount,
        "include_astro_row": True,
        "include_service_row": True,
        "gotra": booking.get("gotra"),
        "nakshatra": booking.get("nakshatra") or booking.get("star"),
        "rashi": booking.get("rashi"),
        "service_date": _format_receipt_date(booking.get("seva_date") or booking.get("booking_date") or booking.get("created_at")),
        "note_english": "Note: Sevakartas to be present 10 minutes before Pooja time for Sankalpa and collect the prasadam on the same day.",
        "powered_by_line": "Powered by Sanmitra Tech Solutions.",
        "local_language": temple_profile.get("local_language"),
        "use_local_labels": True,
    }
    return _build_receipt_pdf_bytes(payload)
_ONES_WORDS = [
    "ZERO",
    "ONE",
    "TWO",
    "THREE",
    "FOUR",
    "FIVE",
    "SIX",
    "SEVEN",
    "EIGHT",
    "NINE",
    "TEN",
    "ELEVEN",
    "TWELVE",
    "THIRTEEN",
    "FOURTEEN",
    "FIFTEEN",
    "SIXTEEN",
    "SEVENTEEN",
    "EIGHTEEN",
    "NINETEEN",
]
_TENS_WORDS = ["", "", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]
_KANNADA_ONES_WORDS = [
    "ಸೊನ್ನೆ",
    "ಒಂದು",
    "ಎರಡು",
    "ಮೂರು",
    "ನಾಲ್ಕು",
    "ಐದು",
    "ಆರು",
    "ಏಳು",
    "ಎಂಟು",
    "ಒಂಬತ್ತು",
    "ಹತ್ತು",
    "ಹನ್ನೊಂದು",
    "ಹನ್ನೆರಡು",
    "ಹದಿಮೂರು",
    "ಹದಿನಾಲ್ಕು",
    "ಹದಿನೈದು",
    "ಹದಿನಾರು",
    "ಹದಿನೇಳು",
    "ಹದಿನೆಂಟು",
    "ಹತ್ತೊಂಬತ್ತು",
]
_KANNADA_TENS_WORDS = {
    20: "ಇಪ್ಪತ್ತು",
    30: "ಮೂವತ್ತು",
    40: "ನಲವತ್ತು",
    50: "ಐವತ್ತು",
    60: "ಅರವತ್ತು",
    70: "ಎಪ್ಪತ್ತು",
    80: "ಎಂಬತ್ತು",
    90: "ತೊಂಬತ್ತು",
}
_KANNADA_COMPOUND_TENS_STEMS = {
    20: "\u0c87\u0caa\u0ccd\u0caa\u0ca4\u0ccd",
    30: "\u0cae\u0cc2\u0cb5\u0ca4\u0ccd",
    40: "\u0ca8\u0cb2\u0cb5\u0ca4\u0ccd",
    50: "\u0c90\u0cb5\u0ca4\u0ccd",
    60: "\u0c85\u0cb0\u0cb5\u0ca4\u0ccd",
    70: "\u0c8e\u0caa\u0ccd\u0caa\u0ca4\u0ccd",
    80: "\u0c8e\u0c82\u0cac\u0ca4\u0ccd",
    90: "\u0ca4\u0cca\u0c82\u0cac\u0ca4\u0ccd",
}
_KANNADA_COMPOUND_SUFFIXES = {
    1: "\u0ca4\u0cca\u0c82\u0ca6\u0cc1",
    2: "\u0ca4\u0cc6\u0cb0\u0ca1\u0cc1",
    3: "\u0ca4\u0cae\u0cc2\u0cb0\u0cc1",
    4: "\u0ca8\u0cbe\u0cb2\u0ccd\u0c95\u0cc1",
    5: "\u0ca4\u0cc8\u0ca6\u0cc1",
    6: "\u0ca4\u0cbe\u0cb0\u0cc1",
    7: "\u0ca4\u0cc7\u0cb3\u0cc1",
    8: "\u0ca4\u0cc6\u0c82\u0c9f\u0cc1",
    9: "\u0ca4\u0cca\u0c82\u0cac\u0ca4\u0ccd\u0ca4\u0cc1",
}

_SUPPORTED_LOCAL_LANGUAGES = {"kannada", "tamil", "telugu", "malayalam", "hindi"}
_HTML_LANG_BY_LOCAL_LANGUAGE = {
    "kannada": "kn",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "hindi": "hi",
}

_LOCAL_LABELS = {
    "kannada": {
        "receipt_title": "ರಶೀದಿ",
        "receipt_number": "ರಶೀದಿ ಸಂಖ್ಯೆ",
        "date": "ದಿನಾಂಕ",
        "party": "ಭಕ್ತ",
        "donation_party": "ದಾನಿ",
        "address": "ವಿಳಾಸ",
        "line_item": "ಸೇವಾ ವಿವರ",
        "total": "ಒಟ್ಟು ಮೊತ್ತ",
        "gotra": "ಗೋತ್ರ",
        "nakshatra": "ನಕ್ಷತ್ರ",
        "rashi": "ರಾಶಿ",
        "service_date": "ಸೇವಾ ದಿನಾಂಕ",
        "cashier": "ನಗದುಗಾರ",
        "note": "ಸೂಚನೆ: ಸೇವಾಕರ್ತರು ಪೂಜೆಯ ಸಮಯಕ್ಕಿಂತ 10 ನಿಮಿಷ ಮೊದಲು ಹಾಜರಿರಬೇಕು ಮತ್ತು ಅದೇ ದಿನ ಪ್ರಸಾದವನ್ನು ಪಡೆಯಬೇಕು.",
    },
    "tamil": {
        "receipt_title": "?????",
        "receipt_number": "????? ???",
        "date": "????",
        "party": "????/???????",
        "address": "??????",
        "line_item": "???? ??????",
        "total": "???????",
        "gotra": "?????????",
        "nakshatra": "???????????",
        "rashi": "????",
        "service_date": "???? ????",
        "cashier": "?????????",
        "note": "????????: ???? ??????????? 10 ??????? ?????? ?????? ??????? ??? ?????? ???????? ???????.",
    },
    "telugu": {
        "receipt_title": "?????",
        "receipt_number": "????? ?????",
        "date": "????",
        "party": "????/???????",
        "address": "????????",
        "line_item": "??? ???????",
        "total": "??????",
        "gotra": "??????",
        "nakshatra": "????????",
        "rashi": "????",
        "service_date": "??? ????",
        "cashier": "??????",
        "note": "?????: ??? ???????? 10 ??????? ????? ???? ????? ??????? ??? ????? ?????????.",
    },
    "malayalam": {
        "receipt_title": "?????",
        "receipt_number": "????? ?????",
        "date": "?????",
        "party": "????/???????",
        "address": "??????",
        "line_item": "??? ???????????",
        "total": "???",
        "gotra": "??????",
        "nakshatra": "????????",
        "rashi": "????",
        "service_date": "??? ?????",
        "cashier": "??????",
        "note": "????????: ??? ???? ???????? 10 ???????? ??????? ????? ??????? ??? ????? ??????????.",
    },
    "hindi": {
        "receipt_title": "????",
        "receipt_number": "???? ??????",
        "date": "??????",
        "party": "????/???????",
        "address": "???",
        "line_item": "???? ?????",
        "total": "???",
        "gotra": "?????",
        "nakshatra": "???????",
        "rashi": "????",
        "service_date": "???? ????",
        "cashier": "??????",
        "note": "???: ????? ???? ??? ?? 10 ???? ???? ??? ?? ?????? ??? ??? ??????? ?????",
    },
}

_ENGLISH_LABELS = {
    "receipt_title": "RECEIPT",
    "receipt_number": "Receipt No",
    "date": "Date",
    "party": "Devotee",
    "address": "Address",
    "line_item": "Seva Details",
    "total": "Total",
    "gotra": "Gotra",
    "nakshatra": "Star",
    "rashi": "Rashi",
    "service_date": "Seva Date",
    "cashier": "Cashier",
}

_SCRIPT_RANGES = {
    "kannada": (0x0C80, 0x0CFF),
    "tamil": (0x0B80, 0x0BFF),
    "telugu": (0x0C00, 0x0C7F),
    "malayalam": (0x0D00, 0x0D7F),
    "hindi": (0x0900, 0x097F),
}

_SCRIPT_FONT_FILES = {
    "kannada": ["NotoSansKannada-Regular.ttf", "NotoSansKannada-Bold.ttf", "Tunga.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "tamil": ["NotoSansTamil-Regular.ttf", "NotoSansTamil-Bold.ttf", "Latha.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "telugu": ["NotoSansTelugu-Regular.ttf", "NotoSansTelugu-Bold.ttf", "Gautami.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "malayalam": ["NotoSansMalayalam-Regular.ttf", "NotoSansMalayalam-Bold.ttf", "Kartika.ttf", "Nirmala.ttc", "Nirmala.ttf"],
    "hindi": ["NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf", "Mangal.ttf", "Nirmala.ttc", "Nirmala.ttf"],
}

_GENERIC_FONT_FILES = ["Nirmala.ttc", "Nirmala.ttf", "NirmalaB.ttf"]
_FONT_SEARCH_DIRS = [
    r"C:\Windows\Fonts",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/opentype/noto",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    "/app/fonts",
    str(MANDIR_COMPAT_DATA_DIR / "fonts"),
]




# ════════════════════════════════════════════════════════════════════════
# SECTION: AMOUNT TO WORDS (English + Kannada)
# NOTE   : _integer_to_words, _amount_to_words, _integer_to_kannada_words, _amount_to_kannada_words, _amount_words_receipt_line
# ════════════════════════════════════════════════════════════════════════

def _integer_to_words(value: int) -> str:
    if value < 20:
        return _ONES_WORDS[value]
    if value < 100:
        tens = _TENS_WORDS[value // 10]
        remainder = value % 10
        return f"{tens} {_ONES_WORDS[remainder]}".strip() if remainder else tens
    if value < 1000:
        hundreds = f"{_ONES_WORDS[value // 100]} HUNDRED"
        remainder = value % 100
        return f"{hundreds} {_integer_to_words(remainder)}".strip() if remainder else hundreds
    if value < 100000:
        thousands = f"{_integer_to_words(value // 1000)} THOUSAND"
        remainder = value % 1000
        return f"{thousands} {_integer_to_words(remainder)}".strip() if remainder else thousands
    if value < 10000000:
        lakhs = f"{_integer_to_words(value // 100000)} LAKH"
        remainder = value % 100000
        return f"{lakhs} {_integer_to_words(remainder)}".strip() if remainder else lakhs
    crores = f"{_integer_to_words(value // 10000000)} CRORE"
    remainder = value % 10000000
    return f"{crores} {_integer_to_words(remainder)}".strip() if remainder else crores



def _amount_to_words(amount: float) -> str:
    try:
        major = int(round(float(amount or 0)))
    except Exception:
        major = 0
    return f"{_integer_to_words(max(major, 0))} ONLY"


def _integer_to_kannada_words(value: int) -> str:
    if value < 20:
        return _KANNADA_ONES_WORDS[value]
    if value < 100:
        tens_value = (value // 10) * 10
        remainder = value % 10
        tens = _KANNADA_TENS_WORDS[tens_value]
        if remainder:
            stem = _KANNADA_COMPOUND_TENS_STEMS.get(tens_value)
            suffix = _KANNADA_COMPOUND_SUFFIXES.get(remainder)
            if stem and suffix:
                return f"{stem}{suffix}"
        return f"{tens} {_KANNADA_ONES_WORDS[remainder]}".strip() if remainder else tens
    if value < 1000:
        hundreds = f"{_KANNADA_ONES_WORDS[value // 100]} ನೂರು"
        remainder = value % 100
        return f"{hundreds} {_integer_to_kannada_words(remainder)}".strip() if remainder else hundreds
    if value < 100000:
        thousands = f"{_integer_to_kannada_words(value // 1000)} ಸಾವಿರ"
        remainder = value % 1000
        return f"{thousands} {_integer_to_kannada_words(remainder)}".strip() if remainder else thousands
    if value < 10000000:
        lakhs = f"{_integer_to_kannada_words(value // 100000)} ಲಕ್ಷ"
        remainder = value % 100000
        return f"{lakhs} {_integer_to_kannada_words(remainder)}".strip() if remainder else lakhs
    crores = f"{_integer_to_kannada_words(value // 10000000)} ಕೋಟಿ"
    remainder = value % 10000000
    return f"{crores} {_integer_to_kannada_words(remainder)}".strip() if remainder else crores


def _amount_to_kannada_words(amount: float) -> str:
    try:
        major = int(round(float(amount or 0)))
    except Exception:
        major = 0
    return f"ರೂಪಾಯಿ {_integer_to_kannada_words(max(major, 0))} ಮಾತ್ರ"


def _amount_words_receipt_line(amount: float, *, local_language: str | None = None) -> str:
    english = f"Rupees {_amount_to_words(amount).title()}"
    if _normalize_local_language(local_language) == "kannada":
        return f"{_amount_to_kannada_words(amount)} / {english}"
    return f"Received {english}"




# ════════════════════════════════════════════════════════════════════════
# SECTION: RECEIPT TEXT COMPOSITION
# NOTE   : _as_text, _first_non_empty_text, _name_prefix_from_sources, _compose_receipt_party_name, _compose_receipt_address_line, _split_amount, _normalize_local_language, _detect_script
# ════════════════════════════════════════════════════════════════════════

def _as_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback




def _first_non_empty_text(*values: Any) -> str:
    for value in values:
        text = _as_text(value)
        if text:
            return text
    return ""


def _name_prefix_from_sources(*sources: Any) -> str:
    for source in sources:
        if not isinstance(source, dict):
            continue
        prefix = _first_non_empty_text(
            source.get("name_prefix"),
            source.get("devotee_prefix"),
            source.get("prefix"),
            source.get("title"),
            source.get("salutation"),
        )
        if prefix:
            return prefix
    return ""


def _compose_receipt_party_name(*sources: Any, fallback: str = "Devotee") -> str:
    name_value = ""
    for source in sources:
        if not isinstance(source, dict):
            continue
        name_value = _first_non_empty_text(
            source.get("devotee_name"),
            source.get("devotee_names"),
            source.get("name"),
            source.get("full_name"),
            source.get("first_name"),
        )
        if name_value:
            break

    if not name_value:
        return fallback

    prefix_value = _name_prefix_from_sources(*sources)
    if not prefix_value:
        return name_value

    normalized_prefix = " ".join(prefix_value.replace(".", " ").split()).lower()
    normalized_name = " ".join(name_value.replace(".", " ").split()).lower()
    if normalized_name.startswith(f"{normalized_prefix} ") or normalized_name == normalized_prefix:
        return name_value
    return f"{prefix_value} {name_value}".strip()


def _compose_receipt_address_line(*sources: Any, fallback: str = "--") -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("devotee_address", "address", "city", "state", "pincode"):
            part = _as_text(source.get(key))
            if not part:
                continue
            normalized = " ".join(part.replace(",", " ").split()).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            parts.append(part)
    return ", ".join(parts) if parts else fallback

def _split_amount(value: Any) -> tuple[str, str]:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    normalized = f"{amount:.2f}"
    major, minor = normalized.split(".", 1)
    return major, minor



def _normalize_local_language(value: Any) -> str | None:
    if value is None:
        return None
    language = str(value).strip().lower()
    language = {
        "kannada": "kannada",
        "kan": "kannada",
        "tamil": "tamil",
        "tam": "tamil",
        "telugu": "telugu",
        "tel": "telugu",
        "malayalam": "malayalam",
        "mal": "malayalam",
        "hindi": "hindi",
        "hin": "hindi",
    }.get(language, language)
    return language if language in _SUPPORTED_LOCAL_LANGUAGES else None



def _detect_script(text: str) -> str | None:
    for char in text:
        code = ord(char)
        for script_name, (start, end) in _SCRIPT_RANGES.items():
            if start <= code <= end:
                return script_name
    return None




# ════════════════════════════════════════════════════════════════════════
# SECTION: FONT RESOLUTION + REPORTLAB STYLES
# NOTE   : _font_candidate_paths, _resolve_font_name, _receipt_paragraph, _format_receipt_date, _format_payment_mode_for_receipt, _format_payment_mode_local, _receipt_payment_line, _compose_receipt_line_description, _extract_seva_line_items
# ════════════════════════════════════════════════════════════════════════

def _font_candidate_paths(script_hint: str | None) -> list[str]:
    candidates: list[str] = []
    script_files = _SCRIPT_FONT_FILES.get(script_hint or "", [])
    for file_name in script_files:
        for search_dir in _FONT_SEARCH_DIRS:
            candidates.append(os.path.join(search_dir, file_name))
    for file_name in _GENERIC_FONT_FILES:
        for search_dir in _FONT_SEARCH_DIRS:
            candidates.append(os.path.join(search_dir, file_name))
    seen: set[str] = set()
    deduped: list[str] = []
    for p in candidates:
        normalized = os.path.normpath(p)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped



def _resolve_font_name(script_hint: str | None) -> str:
    for idx, font_path in enumerate(_font_candidate_paths(script_hint)):
        if not os.path.exists(font_path):
            continue
        font_name = f"MandirReceipt_{script_hint or 'generic'}_{idx}"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            except Exception:
                continue
        return font_name
    return "Helvetica"



def _receipt_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    raw_text = _as_text(text, "-")
    pieces: list[str] = []
    buffer: list[str] = []
    buffer_is_latin: bool | None = None

    def flush_buffer() -> None:
        nonlocal buffer, buffer_is_latin
        if not buffer:
            return
        escaped_text = escape("".join(buffer))
        if buffer_is_latin and style.fontName != "Helvetica":
            pieces.append(f'<font name="Helvetica">{escaped_text}</font>')
        elif not buffer_is_latin and style.fontName != "Helvetica":
            pieces.append(f'<font name="{style.fontName}">{escaped_text}</font>')
        else:
            pieces.append(escaped_text)
        buffer = []
        buffer_is_latin = None

    for char in raw_text:
        if char == "\n":
            flush_buffer()
            pieces.append("<br/>")
            continue

        is_latin = ord(char) < 128
        if buffer_is_latin is None:
            buffer_is_latin = is_latin
        elif buffer_is_latin != is_latin:
            flush_buffer()
            buffer_is_latin = is_latin
        buffer.append(char)

    flush_buffer()
    return Paragraph("".join(pieces), style)



def _format_receipt_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d/%m/%Y")
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%d/%m/%Y")
    except Exception:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).strftime("%d/%m/%Y")
            except Exception:
                continue
    return raw



def _format_payment_mode_for_receipt(value: Any) -> str:
    mode = _as_text(value, "Cash")
    lowered = mode.lower()
    if "cash" in lowered:
        return "Cash"
    if "upi" in lowered:
        return mode
    if any(token in lowered for token in ["upi", "bank", "cheque", "check", "online", "transfer", "neft", "rtgs", "card"]):
        return f"Bank ({mode})"
    return mode


def _format_payment_mode_local_for_receipt(value: Any, *, local_language: str | None = None) -> str:
    if _normalize_local_language(local_language) != "kannada":
        return _format_payment_mode_for_receipt(value)
    mode = _as_text(value, "Cash")
    lowered = mode.lower()
    if "cash" in lowered:
        return "ನಗದು"
    if "cheque" in lowered or "check" in lowered:
        return "ಚೆಕ್"
    if "upi" in lowered:
        return "ಯುಪಿಐ"
    if any(token in lowered for token in ["online", "bank", "transfer", "neft", "rtgs", "card"]):
        return "ಆನ್‌ಲೈನ್ / ಬ್ಯಾಂಕ್"
    return mode


def _receipt_payment_line(
    *,
    payment_mode: str,
    local_language: str | None = None,
    purpose: str = "donation",
) -> str:
    if _normalize_local_language(local_language) != "kannada":
        if purpose == "seva":
            return f"Received with thanks for the below mentioned seva by {payment_mode}."
        return f"Received with thanks for donation by {payment_mode}."
    local_mode = _format_payment_mode_local_for_receipt(payment_mode, local_language=local_language)
    if purpose == "seva":
        return f"ಈ ಕೆಳಗೆ ಕಾಣಿಸಿದ ಸೇವೆಯ ಸಲುವಾಗಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ಪಾವತಿ ವಿಧಾನ: {local_mode} / Received with thanks for the below mentioned seva by {payment_mode}."
    return f"ಧನ್ಯವಾದಗಳೊಂದಿಗೆ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ಪಾವತಿ ವಿಧಾನ: {local_mode} / Received by {payment_mode}."



def _compose_receipt_line_description(name: Any, local_name: Any = None, *, use_local_labels: bool = False) -> str:
    english = _as_text(name, "Seva").strip() or "Seva"
    local = _as_text(local_name, "").strip()
    if use_local_labels and local and local != english:
        return f"{local} / {english}"
    return english


def _extract_seva_line_items(
    booking: dict[str, Any],
    *,
    fallback_name: str,
    fallback_amount: float,
    use_local_labels: bool = False,
) -> list[dict[str, Any]]:
    line_items: list[dict[str, Any]] = []
    candidate_lists = [booking.get("line_items"), booking.get("seva_items"), booking.get("sevas"), booking.get("booked_sevas")]
    for candidate in candidate_lists:
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if not isinstance(item, dict):
                continue
            name = _as_text(item.get("description") or item.get("seva_name") or item.get("name"), "")
            local_name = _as_text(
                item.get("description_local")
                or item.get("seva_name_local")
                or item.get("name_kannada")
                or item.get("local_name"),
                "",
            )
            amount = _safe_float(item.get("amount") or item.get("amount_paid") or item.get("fee"), 0.0)
            if not name and amount <= 0:
                continue
            line_items.append({
                "description": _compose_receipt_line_description(name or fallback_name, local_name, use_local_labels=use_local_labels),
                "amount": amount or fallback_amount,
            })

    if not line_items:
        csv_names = _as_text(booking.get("seva_names"))
        if csv_names:
            names = [part.strip() for part in csv_names.split(",") if part.strip()]
            if names:
                split_amount = fallback_amount / len(names) if fallback_amount > 0 else 0.0
                for name in names:
                    line_items.append({"description": name, "amount": split_amount})

    if not line_items:
        line_items = [{"description": fallback_name, "amount": fallback_amount}]
    return line_items




# ════════════════════════════════════════════════════════════════════════
# SECTION: TEMPLE RECEIPT PROFILE
# NOTE   : _build_temple_receipt_profile, _resolve_temple_receipt_profile, _bilingual_label
# ════════════════════════════════════════════════════════════════════════

def _build_temple_receipt_profile(temple_doc: dict[str, Any] | None) -> dict[str, str | None]:
    temple_doc = temple_doc if isinstance(temple_doc, dict) else {}
    temple_name = _as_text(temple_doc.get("temple_name") or temple_doc.get("name"), "Temple")
    trust_name = _as_text(temple_doc.get("trust_name"), temple_name)
    address = _as_text(temple_doc.get("address") or temple_doc.get("temple_address"))
    city = _as_text(temple_doc.get("city") or temple_doc.get("city_name"))
    state = _as_text(temple_doc.get("state") or temple_doc.get("state_name"))
    pincode = _as_text(temple_doc.get("pincode"))
    email = _as_text(temple_doc.get("email") or temple_doc.get("temple_email"))
    phone = _as_text(temple_doc.get("phone") or temple_doc.get("contact_number") or temple_doc.get("temple_contact_number"))
    website = _as_text(temple_doc.get("website") or temple_doc.get("temple_website"))
    header_local_line = _as_text(temple_doc.get("header_local_line"))
    local_language = _normalize_local_language(
        temple_doc.get("receipt_local_language")
        or temple_doc.get("local_language")
        or temple_doc.get("primary_language")
        or temple_doc.get("language")
    )
    if local_language == "kannada" and temple_name == "Temple":
        temple_name = "ದೇವಸ್ಥಾನ"
        if trust_name == "Temple":
            trust_name = temple_name
    return {
        "trust_name": trust_name,
        "temple_name": temple_name,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
        "email": email,
        "phone": phone,
        "website": website,
        "header_local_line": header_local_line,
        "local_language": local_language,
    }



async def _resolve_temple_receipt_profile(
    *,
    tenant_id: str,
    app_key: str,
    lang: str | None = None,
) -> dict[str, str | None]:
    temple_doc: dict[str, Any] = {}
    try:
        temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
        if not temple_doc:
            temple_doc = await mandir_router.get_collection("mandir_temples").find_one({"tenant_id": tenant_id}) or {}
    except Exception as exc:
        logger.warning("Mandir receipt temple profile lookup failed for tenant=%s app=%s: %s", tenant_id, app_key, exc)

    lang_doc: dict[str, Any] = {}
    try:
        lang_doc = await mandir_router.get_collection("mandir_panchang_settings").find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    except Exception as exc:
        logger.warning("Mandir receipt language lookup failed for tenant=%s app=%s: %s", tenant_id, app_key, exc)

    temple_profile = _build_temple_receipt_profile(temple_doc)
    selected_language = _normalize_local_language(
        lang
        or lang_doc.get("receipt_local_language")
        or temple_doc.get("receipt_local_language")
        or lang_doc.get("local_language")
        or temple_doc.get("local_language")
        or lang_doc.get("primary_language")
        or temple_doc.get("primary_language")
        or temple_profile.get("local_language")
        or "kannada"
    )
    temple_profile["local_language"] = selected_language or "kannada"
    return temple_profile


def _bilingual_label(local_label: str, english_label: str, use_local_labels: bool) -> str:
    if use_local_labels and local_label:
        return f"{local_label} / {english_label}"
    return english_label




# ════════════════════════════════════════════════════════════════════════
# SECTION: WEASYPRINT + BILINGUAL LABEL HELPERS
# NOTE   : _default_labels, _receipt_html_escape, _receipt_html_mixed, _receipt_weasy_font_css (entry)
# ════════════════════════════════════════════════════════════════════════

def _default_labels(local_language: str | None, use_local_labels: bool) -> dict[str, str]:
    local_labels = _LOCAL_LABELS.get(local_language or "", {})
    return {
        "receipt_title": _bilingual_label(local_labels.get("receipt_title", ""), _ENGLISH_LABELS["receipt_title"], use_local_labels),
        "receipt_number": _bilingual_label(local_labels.get("receipt_number", ""), _ENGLISH_LABELS["receipt_number"], use_local_labels),
        "date": _bilingual_label(local_labels.get("date", ""), _ENGLISH_LABELS["date"], use_local_labels),
        "party": _bilingual_label(local_labels.get("party", ""), _ENGLISH_LABELS["party"], use_local_labels),
        "address": _bilingual_label(local_labels.get("address", ""), _ENGLISH_LABELS["address"], use_local_labels),
        "line_item": _bilingual_label(local_labels.get("line_item", ""), _ENGLISH_LABELS["line_item"], use_local_labels),
        "total": _bilingual_label(local_labels.get("total", ""), _ENGLISH_LABELS["total"], use_local_labels),
        "gotra": _bilingual_label(local_labels.get("gotra", ""), _ENGLISH_LABELS["gotra"], use_local_labels),
        "nakshatra": _bilingual_label(local_labels.get("nakshatra", ""), _ENGLISH_LABELS["nakshatra"], use_local_labels),
        "rashi": _bilingual_label(local_labels.get("rashi", ""), _ENGLISH_LABELS["rashi"], use_local_labels),
        "service_date": _bilingual_label(local_labels.get("service_date", ""), _ENGLISH_LABELS["service_date"], use_local_labels),
        "cashier": _bilingual_label(local_labels.get("cashier", ""), _ENGLISH_LABELS["cashier"], use_local_labels),
        "note_local": local_labels.get("note", ""),
    }


def _receipt_html_escape(value: Any, fallback: str = "-") -> str:
    return escape(_as_text(value, fallback), {'"': "&quot;", "'": "&#x27;"})


def _receipt_html_mixed(value: Any, fallback: str = "-") -> str:
    raw_text = _as_text(value, fallback)
    pieces: list[str] = []
    buffer: list[str] = []
    buffer_is_latin: bool | None = None

    def flush_buffer() -> None:
        nonlocal buffer, buffer_is_latin
        if not buffer:
            return
        escaped_text = escape("".join(buffer), {'"': "&quot;", "'": "&#x27;"})
        if buffer_is_latin:
            pieces.append(f'<span class="latin">{escaped_text}</span>')
        else:
            pieces.append(escaped_text)
        buffer = []
        buffer_is_latin = None

    for char in raw_text:
        if char == "\n":
            flush_buffer()
            pieces.append("<br/>")
            continue

        is_latin = ord(char) < 128
        if buffer_is_latin is None:
            buffer_is_latin = is_latin
        elif buffer_is_latin != is_latin:
            flush_buffer()
            buffer_is_latin = is_latin
        buffer.append(char)

    flush_buffer()
    return "".join(pieces)


def _receipt_weasy_font_css(local_language: str | None) -> str:
    candidates = []
    for candidate in _font_candidate_paths(local_language):
        path = Path(candidate)
        if path.exists() and path.suffix.lower() in {".ttf", ".otf", ".ttc"}:
            candidates.append(path)
    nirmala = Path(r"C:\Windows\Fonts\Nirmala.ttc")
    if nirmala.exists():
        candidates.append(nirmala)

    if not candidates:
        return ""

    font_faces = []
    for index, path in enumerate(candidates[:3]):
        font_faces.append(
            "@font-face {"
            f"font-family: 'MandirReceiptLocal{index}';"
            f"src: url('{path.resolve().as_uri()}');"
            "}"
        )
    return "\n".join(font_faces)



# ════════════════════════════════════════════════════════════════════════
# SECTION: WEASYPRINT RECEIPT PDF BUILDER
# NOTE   : _build_receipt_pdf_bytes_weasy, _receipt_weasy_font_css — HTML-to-PDF receipt via WeasyPrint
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes_weasy(
    payload: dict[str, Any],
    *,
    local_language: str,
    labels: dict[str, str],
    local_labels: dict[str, str],
    use_local_labels: bool,
) -> bytes:
    if HTML is None:
        raise RuntimeError("weasyprint is not available")

    line_items = payload.get("line_items") or []
    if not line_items:
        line_items = [{"description": "-", "amount": payload.get("total_amount", 0)}]

    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    def bilingual(local_key: str, english_value: Any, fallback_key: str) -> str:
        english = _as_text(english_value)
        if not english:
            return labels[fallback_key]
        local = _as_text(payload.get(f"{local_key}_local")) or local_labels.get(local_key, "")
        return _bilingual_label(local, english, use_local_labels)

    receipt_title = bilingual("receipt_title", payload.get("receipt_title"), "receipt_title")
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label = labels["party"] if payload.get("party_label") is None else _as_text(payload.get("party_label"), "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header = bilingual("line_item", payload.get("line_item_header"), "line_item")
    total_label = _as_text(payload.get("total_label")) or labels["total"]
    gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
    star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
    rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
    service_date_label = bilingual("service_date", payload.get("service_date_label"), "service_date")

    header_local_line = _as_text(payload.get("header_local_line"))
    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""
    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )

    header_parts = []
    if header_local_line:
        header_parts.append(f"<div class='local-header'>{_receipt_html_mixed(header_local_line)}</div>")
    header_parts.append(f"<div class='trust'>{_receipt_html_mixed(primary_header)}</div>")
    if secondary_header:
        header_parts.append(f"<div class='temple'>{_receipt_html_mixed(secondary_header)}</div>")
    if address_line:
        header_parts.append(f"<div>{_receipt_html_mixed(address_line)}</div>")
    if _as_text(payload.get("website")):
        header_parts.append(f"<div>{_receipt_html_mixed(payload.get('website'))}</div>")
    if _as_text(payload.get("email")):
        header_parts.append(f"<div>{_receipt_html_mixed(payload.get('email'))}</div>")
    if _as_text(payload.get("phone")):
        header_parts.append(f"<div>{_receipt_html_mixed('Phone')}: {_receipt_html_mixed(payload.get('phone'))}</div>")

    rows_html = []
    for item in line_items:
        major, minor = _split_amount(item.get("amount"))
        rows_html.append(
            "<tr>"
            f"<td class='desc'>{_receipt_html_mixed(item.get('description'))}</td>"
            f"<td class='amt amt-major'>{_receipt_html_mixed(major)}</td>"
            f"<td class='amt amt-minor'>{_receipt_html_mixed(minor)}</td>"
            "</tr>"
        )

    total_major, total_minor = _split_amount(total_amount)
    rows_html.append(
        "<tr>"
        f"<td class='desc total'>{_receipt_html_mixed(total_label)}</td>"
        f"<td class='amt amt-major total'>{_receipt_html_mixed(total_major)}</td>"
        f"<td class='amt amt-minor total'>{_receipt_html_mixed(total_minor)}</td>"
        "</tr>"
    )

    include_note_row = bool(payload.get("include_note_row", True))
    note_lines = [
        _as_text(payload.get("note_local"), labels.get("note_local", "")) if use_local_labels and include_note_row else "",
        _as_text(payload.get("note_english"), "") if include_note_row else "",
    ]
    note_html = "<br/>".join(_receipt_html_mixed(line) for line in note_lines if line)

    astro_html = ""
    if bool(payload.get("include_astro_row", True)):
        astro_html = (
            "<div class='meta-row'>"
            f"{_receipt_html_mixed(gotra_label)}: {_receipt_html_mixed(payload.get('gotra'), '--')}"
            f"&nbsp;&nbsp; {_receipt_html_mixed(star_label)}: {_receipt_html_mixed(payload.get('nakshatra'), '--')}"
            f"&nbsp;&nbsp; {_receipt_html_mixed(rashi_label)}: {_receipt_html_mixed(payload.get('rashi'), '--')}"
            "</div>"
        )

    service_html = ""
    if bool(payload.get("include_service_row", True)):
        service_html = (
            "<div class='meta-row'>"
            f"{_receipt_html_mixed(service_date_label)}: {_receipt_html_mixed(payload.get('service_date'), '--')}"
            "</div>"
        )

    system_line = payload.get("system_generated_line")
    if system_line is None:
        system_line = "This is a system generated receipt and does not require any signature."

    css = f"""
    {_receipt_weasy_font_css(local_language)}
    @page {{ size: A5; margin: 8mm; }}
    body {{
        font-family: 'MandirReceiptLocal0', 'MandirReceiptLocal1', 'Nirmala UI', Arial, sans-serif;
        font-size: 9px;
        line-height: 1.35;
        color: #111;
        font-variant-ligatures: normal;
        font-feature-settings: "kern" 1, "liga" 1, "clig" 1;
        text-rendering: optimizeLegibility;
    }}
    .header {{ text-align: center; margin-bottom: 5px; }}
    .trust {{ font-weight: 700; font-size: 12px; }}
    .temple {{ font-size: 9px; }}
    .local-header {{ font-weight: 700; font-size: 11px; }}
    table.receipt {{ width: 100%; border-collapse: collapse; border: 1px solid #888; }}
    table.receipt td {{ border: 1px solid #aaa; padding: 4px 6px; vertical-align: middle; }}
    .title {{ text-align: center; font-weight: 700; background: #f2f2f2; font-size: 10px; }}
    .right {{ text-align: right; }}
    .date-cell {{ text-align: right; white-space: nowrap; }}
    .center {{ text-align: center; }}
    .desc {{ width: 78%; }}
    .amt-major {{ width: 14%; text-align: right; }}
    .amt-minor {{ width: 8%; text-align: center; }}
    .total {{ font-weight: 700; }}
    .note {{ text-align: center; background: #f8f8f8; }}
    .meta-row {{ margin-top: 5px; font-size: 8px; }}
    .powered {{ text-align: right; color: #555; font-size: 7px; margin-top: 4px; }}
    .latin {{ font-family: Arial, 'DejaVu Sans', sans-serif; }}
    """
    html_lang = _HTML_LANG_BY_LOCAL_LANGUAGE.get(local_language, local_language)
    html = f"""
    <!doctype html>
    <html lang="{_receipt_html_escape(html_lang)}">
    <head><meta charset="utf-8"/><style>{css}</style></head>
    <body>
      <div class="header">{''.join(header_parts)}</div>
      <table class="receipt">
        <tr><td class="title" colspan="3">{_receipt_html_mixed(receipt_title)}</td></tr>
        <tr>
          <td>{_receipt_html_mixed(receipt_no_label)}: {_receipt_html_mixed(payload.get('receipt_number'), '-')}</td>
          <td class="date-cell" colspan="2">{_receipt_html_mixed(date_label)}: {_receipt_html_mixed(payload.get('receipt_date'), '-')}</td>
        </tr>
        <tr><td colspan="3">{_receipt_html_mixed(party_label)}: {_receipt_html_mixed(payload.get('party_name'), '-')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(address_label)}: {_receipt_html_mixed(payload.get('address_value'), '--')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(payload.get('amount_words_line'), 'Received with thanks')}</td></tr>
        <tr><td colspan="3">{_receipt_html_mixed(payload.get('payment_line'), 'Received with thanks.')}</td></tr>
        <tr>
          <td class="desc total">{_receipt_html_mixed(line_item_header)}</td>
          <td class="center total amt-major">Rs</td>
          <td class="center total amt-minor"></td>
        </tr>
        {''.join(rows_html)}
        {f'<tr><td class="note" colspan="3">{note_html or "-"}</td></tr>' if include_note_row else ''}
      </table>
      {astro_html}
      {service_html}
      <div class="center">{_receipt_html_mixed(system_line, '')}</div>
      <div class="powered">{_receipt_html_mixed(payload.get('powered_by_line'), '')}</div>
    </body>
    </html>
    """
    return HTML(string=html, base_url=str(Path.cwd().resolve())).write_pdf()



# ════════════════════════════════════════════════════════════════════════
# SECTION: PILLOW FONT + TEXT RENDERING HELPERS
# NOTE   : _load_receipt_pillow_font, _load_receipt_latin_pillow_font, _receipt_text_runs, _draw_receipt_text, _receipt_text_width, _wrap_receipt_text, _draw_receipt_cell_text
# ════════════════════════════════════════════════════════════════════════

def _load_receipt_pillow_font(script_hint: str | None, size_px: int) -> Any:
    if ImageFont is None:
        raise RuntimeError("Pillow font support is not available")
    for font_path in _font_candidate_paths(script_hint):
        path = Path(font_path)
        if not path.exists() or path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
            continue
        try:
            return ImageFont.truetype(str(path), size_px)
        except Exception:
            continue
    return ImageFont.load_default()


def _load_receipt_latin_pillow_font(size_px: int) -> Any:
    if ImageFont is None:
        raise RuntimeError("Pillow font support is not available")
    for candidate in [
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        if not Path(candidate).exists():
            continue
        try:
            return ImageFont.truetype(candidate, size_px)
        except Exception:
            continue
    return ImageFont.load_default()


def _receipt_text_runs(text: str) -> list[tuple[str, bool]]:
    runs: list[tuple[str, bool]] = []
    current: list[str] = []
    current_is_latin: bool | None = None
    for char in text:
        is_latin = ord(char) < 128
        if current_is_latin is None:
            current_is_latin = is_latin
        elif current_is_latin != is_latin:
            runs.append(("".join(current), current_is_latin))
            current = []
            current_is_latin = is_latin
        current.append(char)
    if current:
        runs.append(("".join(current), bool(current_is_latin)))
    return runs


def _draw_receipt_text(
    draw: Any,
    xy: tuple[int, int],
    text: str,
    font: Any,
    *,
    latin_font: Any | None = None,
    fill: str = "#111111",
    anchor: str | None = None,
) -> None:
    if latin_font is not None and text and anchor in {"la", "ma", "ra"}:
        width = _receipt_text_width(draw, text, font, latin_font=latin_font)
        x, y = xy
        if anchor == "ma":
            x -= width // 2
        elif anchor == "ra":
            x -= width
        for run, is_latin in _receipt_text_runs(text):
            run_font = latin_font if is_latin else font
            draw.text((x, y), run, font=run_font, fill=fill)
            x += _receipt_text_width(draw, run, run_font)
        return
    kwargs = {"font": font, "fill": fill}
    if anchor:
        kwargs["anchor"] = anchor
    draw.text(xy, text, **kwargs)


def _receipt_text_width(draw: Any, text: str, font: Any, *, latin_font: Any | None = None) -> int:
    if latin_font is not None:
        return sum(
            _receipt_text_width(draw, run, latin_font if is_latin else font)
            for run, is_latin in _receipt_text_runs(text)
        )
    try:
        return int(draw.textlength(text, font=font))
    except Exception:
        bbox = draw.textbbox((0, 0), text, font=font)
        return int(bbox[2] - bbox[0])


def _wrap_receipt_text(draw: Any, text: str, font: Any, max_width: int, *, latin_font: Any | None = None) -> list[str]:
    words = _as_text(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _receipt_text_width(draw, candidate, font, latin_font=latin_font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def _draw_receipt_cell_text(
    draw: Any,
    rect: tuple[int, int, int, int],
    text: str,
    font: Any,
    *,
    latin_font: Any | None = None,
    align: str = "left",
    bold_font: Any | None = None,
    max_lines: int = 2,
) -> None:
    x1, y1, x2, y2 = rect
    pad = 10
    selected_font = bold_font or font
    selected_latin_font = latin_font
    lines = _wrap_receipt_text(
        draw,
        _as_text(text, "-"),
        selected_font,
        max(10, x2 - x1 - (pad * 2)),
        latin_font=selected_latin_font,
    )[:max_lines]
    line_height = int(selected_font.size * 1.25) if hasattr(selected_font, "size") else 18
    total_height = line_height * len(lines)
    y = y1 + max(0, ((y2 - y1) - total_height) // 2)
    for line in lines:
        if align == "right":
            x = x2 - pad
            anchor = "ra"
        elif align == "center":
            x = (x1 + x2) // 2
            anchor = "ma"
        else:
            x = x1 + pad
            anchor = "la"
        _draw_receipt_text(draw, (x, y), line, selected_font, latin_font=selected_latin_font, anchor=anchor)
        y += line_height



# ════════════════════════════════════════════════════════════════════════
# SECTION: PILLOW IMAGE RECEIPT BUILDER
# NOTE   : _build_receipt_pdf_bytes_pillow — renders receipt as PNG wrapped in PDF using Pillow
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes_pillow(
    payload: dict[str, Any],
    *,
    local_language: str,
    labels: dict[str, str],
    local_labels: dict[str, str],
    use_local_labels: bool,
) -> bytes:
    if PILImage is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow is not available")
    if pil_features is not None and not pil_features.check("raqm"):
        raise RuntimeError("Pillow was built without RAQM/HarfBuzz shaping")

    scale = 3
    page_w_pt, page_h_pt = A5
    page_w = int(page_w_pt * scale)
    page_h = int(page_h_pt * scale)
    image = PILImage.new("RGB", (page_w, page_h), "white")
    draw = ImageDraw.Draw(image)

    font_small = _load_receipt_pillow_font(local_language, 24)
    font_body = _load_receipt_pillow_font(local_language, 28)
    font_header = _load_receipt_pillow_font(local_language, 34)
    font_title = _load_receipt_pillow_font(local_language, 30)
    font_footer = _load_receipt_pillow_font(local_language, 20)
    latin_small = _load_receipt_latin_pillow_font(24)
    latin_body = _load_receipt_latin_pillow_font(28)
    latin_header = _load_receipt_latin_pillow_font(34)
    latin_title = _load_receipt_latin_pillow_font(30)
    latin_footer = _load_receipt_latin_pillow_font(20)

    def p(value: float) -> int:
        return int(value * scale)

    def line(x1: int, y1: int, x2: int, y2: int, width: int = 1) -> None:
        draw.line((x1, y1, x2, y2), fill="#777777", width=max(1, width * scale))

    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""
    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )

    margin = p(10)
    left = margin
    right = page_w - margin
    outer_top = margin
    outer_bottom = page_h - p(52)
    line(left, outer_top, right, outer_top)
    line(left, outer_top, left, outer_bottom)
    line(right, outer_top, right, outer_bottom)
    line(left, outer_bottom, right, outer_bottom)

    header_top = outer_top
    header_bottom = p(100)
    title_bottom = p(120)
    line(left, header_bottom, right, header_bottom)
    line(left, title_bottom, right, title_bottom)

    logo_source = _as_text(payload.get("logo"))
    logo_box = (left + p(4), header_top + p(10), left + p(68), header_bottom - p(4))
    if logo_source and Path(logo_source).exists():
        try:
            logo = PILImage.open(logo_source).convert("RGB")
            logo.thumbnail((logo_box[2] - logo_box[0], logo_box[3] - logo_box[1]))
            logo_x = logo_box[0] + ((logo_box[2] - logo_box[0]) - logo.width) // 2
            logo_y = logo_box[1] + ((logo_box[3] - logo_box[1]) - logo.height) // 2
            image.paste(logo, (logo_x, logo_y))
        except Exception:
            logo_source = ""

    header_left = logo_box[2] + p(8) if logo_source and Path(logo_source).exists() else left
    header_center_x = (header_left + right) // 2
    y = header_top + p(14)
    header_rows = [
        (_as_text(payload.get("header_local_line")), font_title, latin_title),
        (primary_header, font_header, latin_header),
        (address_line, font_small, latin_small),
        (_as_text(payload.get("website")), font_footer, latin_footer),
        (_as_text(payload.get("email")), font_footer, latin_footer),
        (f"Phone : {_as_text(payload.get('phone'))}" if _as_text(payload.get("phone")) else "", font_footer, latin_footer),
    ]
    for text, font, latin_font in header_rows:
        if not text:
            continue
        _draw_receipt_text(draw, (header_center_x, y), text, font, latin_font=latin_font, anchor="ma")
        y += int(font.size * 1.05)

    top = title_bottom
    col1 = left + int((right - left) * 0.73)
    col2 = left + int((right - left) * 0.91)

    line_items = payload.get("line_items") or [{"description": "-", "amount": payload.get("total_amount", 0)}]
    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    def bilingual(local_key: str, english_value: Any, fallback_key: str) -> str:
        english = _as_text(english_value)
        if not english:
            return labels[fallback_key]
        local = _as_text(payload.get(f"{local_key}_local")) or local_labels.get(local_key, "")
        return _bilingual_label(local, english, use_local_labels)

    receipt_title = bilingual("receipt_title", payload.get("receipt_title"), "receipt_title")
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label = labels["party"] if payload.get("party_label") is None else _as_text(payload.get("party_label"), "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header = bilingual("line_item", payload.get("line_item_header"), "line_item")
    total_label = _as_text(payload.get("total_label")) or labels["total"]

    details_top = top
    meta_top = p(417) if bool(payload.get("include_astro_row", True)) else p(395)
    note_top = p(495) if bool(payload.get("include_astro_row", True)) else p(462)
    bottom = outer_bottom
    line(left, details_top, right, details_top)
    line(left, meta_top, right, meta_top)
    if bool(payload.get("include_astro_row", True)):
        line(left, note_top, right, note_top)

    r1 = details_top + p(30)
    r2 = r1 + p(22)
    r3 = r2 + p(22)
    r4 = r3 + p(30)
    r5 = r4 + p(38)
    item_header_top = r5
    item_header_bottom = item_header_top + p(24)
    total_top = meta_top - p(22)

    for y_line in [r1, r2, r3, r4, r5, item_header_bottom, total_top]:
        line(left, y_line, right, y_line)
    line(col1, item_header_top, col1, meta_top)
    line(col2, item_header_bottom, col2, meta_top)

    _draw_receipt_cell_text(draw, (left, header_bottom, right, title_bottom), receipt_title, font_title, latin_font=latin_title, align="center")
    _draw_receipt_cell_text(
        draw,
        (left, details_top, col1, r1),
        f"{receipt_no_label}: {_as_text(payload.get('receipt_number'), '-')}",
        font_body,
        latin_font=latin_body,
    )
    _draw_receipt_cell_text(
        draw,
        (col1, details_top, right, r1),
        f"{date_label}: {_as_text(payload.get('receipt_date'), '-')}",
        font_body,
        latin_font=latin_body,
        align="right",
    )
    _draw_receipt_cell_text(draw, (left, r1, right, r2), f"{party_label}: {_as_text(payload.get('party_name'), '-')}", font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r2, right, r3), f"{address_label}: {_as_text(payload.get('address_value'), '--')}", font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r3, right, r4), _as_text(payload.get("amount_words_line"), "-"), font_body, latin_font=latin_body)
    _draw_receipt_cell_text(draw, (left, r4, right, r5), _as_text(payload.get("payment_line"), "-"), font_body, latin_font=latin_body, max_lines=2)
    _draw_receipt_cell_text(draw, (left, item_header_top, col1, item_header_bottom), line_item_header, font_body, latin_font=latin_body, align="center")
    _draw_receipt_cell_text(draw, (col1, item_header_top, right, item_header_bottom), "ರೂ Rs", font_body, latin_font=latin_body, align="center")

    item_y = item_header_bottom
    item_height = max(p(24), (total_top - item_header_bottom) // max(1, len(line_items)))
    for item in line_items:
        major, minor = _split_amount(item.get("amount"))
        _draw_receipt_cell_text(draw, (left, item_y, col1, min(item_y + item_height, total_top)), _as_text(item.get("description"), "-"), font_body, latin_font=latin_body)
        _draw_receipt_cell_text(draw, (col1, item_y, col2, min(item_y + item_height, total_top)), major, font_body, latin_font=latin_body, align="right")
        _draw_receipt_cell_text(draw, (col2, item_y, right, min(item_y + item_height, total_top)), minor, font_body, latin_font=latin_body, align="center")
        item_y += item_height

    total_major, total_minor = _split_amount(total_amount)
    _draw_receipt_cell_text(draw, (left, total_top, col1, meta_top), total_label, font_body, latin_font=latin_body, align="right")
    _draw_receipt_cell_text(draw, (col1, total_top, col2, meta_top), total_major, font_body, latin_font=latin_body, align="right")
    _draw_receipt_cell_text(draw, (col2, total_top, right, meta_top), total_minor, font_body, latin_font=latin_body, align="center")

    if bool(payload.get("include_astro_row", True)):
        meta_mid = meta_top + p(38)
        gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
        star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
        rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
        service_date_label = bilingual("service_date", payload.get("service_date_label"), "service_date")
        meta_width = (right - left) // 3
        for idx, (label, value) in enumerate([
            (gotra_label, payload.get("gotra")),
            (star_label, payload.get("nakshatra")),
            (rashi_label, payload.get("rashi")),
        ]):
            x1 = left + (meta_width * idx)
            x2 = right if idx == 2 else left + (meta_width * (idx + 1))
            _draw_receipt_cell_text(draw, (x1, meta_top, x2, meta_mid), f"{label}: {_as_text(value, '--')}", font_small, latin_font=latin_small, max_lines=2)
        _draw_receipt_cell_text(
            draw,
            (left, meta_mid, left + p(150), note_top),
            f"{service_date_label}: {_as_text(payload.get('service_date'), '--')}",
            font_small,
            latin_font=latin_small,
            max_lines=2,
        )
        _draw_receipt_cell_text(draw, (right - p(170), meta_mid, right, note_top), labels["cashier"], font_small, latin_font=latin_small, align="center")

    include_note_row = bool(payload.get("include_note_row", True))
    note_lines = [
        _as_text(payload.get("note_local"), labels.get("note_local", "")) if use_local_labels and include_note_row else "",
        _as_text(payload.get("note_english"), "") if include_note_row else "",
    ]
    note_text = "\n".join(line for line in note_lines if line)
    if include_note_row:
        note_rect = (left, note_top if bool(payload.get("include_astro_row", True)) else meta_top, right, bottom)
        _draw_receipt_cell_text(draw, note_rect, note_text, font_small, latin_font=latin_small, align="center", max_lines=4)
    system_line_raw = payload.get("system_generated_line")
    if system_line_raw is None:
        system_line = "This is a system generated receipt and does not require any signature."
    else:
        system_line = str(system_line_raw).strip()
    _draw_receipt_text(draw, (page_w // 2, outer_bottom + p(8)), system_line, font_footer, latin_font=latin_footer, anchor="ma")
    _draw_receipt_text(draw, (right, page_h - p(22)), _as_text(payload.get("powered_by_line"), ""), font_footer, latin_font=latin_footer, anchor="ra", fill="#333333")

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    pdf_buffer = BytesIO()
    canvas = pdf_canvas.Canvas(pdf_buffer, pagesize=A5)
    canvas.drawImage(ImageReader(image_buffer), 0, 0, width=page_w_pt, height=page_h_pt)
    try:
        hidden_font = _resolve_font_name(local_language)
        canvas.setFont(hidden_font, 1)
        canvas.setFillColor(colors.white)
        canvas.drawString(1, 1, receipt_title)
        canvas.drawString(1, 2, _as_text(payload.get("amount_words_line"), ""))
    except Exception:
        pass
    canvas.showPage()
    canvas.save()
    return pdf_buffer.getvalue()




# ════════════════════════════════════════════════════════════════════════
# SECTION: RECEIPT PDF ORCHESTRATOR
# NOTE   : _build_receipt_pdf_bytes — picks WeasyPrint → Pillow → ReportLab strategy
# ════════════════════════════════════════════════════════════════════════

def _build_receipt_pdf_bytes(payload: dict[str, Any]) -> bytes:
    local_language = _normalize_local_language(payload.get("local_language"))
    script_hint = _detect_script(_as_text(payload.get("header_local_line"))) or local_language
    font_name = _resolve_font_name(script_hint)
    has_local_font = font_name != "Helvetica"

    requested_local_labels = payload.get("use_local_labels")
    if requested_local_labels is None:
        requested_local_labels = True
    use_local_labels = bool(requested_local_labels) and has_local_font and local_language in _SUPPORTED_LOCAL_LANGUAGES
    labels = _default_labels(local_language, use_local_labels)
    local_labels = _LOCAL_LABELS.get(local_language or "", {})

    if use_local_labels and local_language:
        try:
            return _build_receipt_pdf_bytes_weasy(
                payload,
                local_language=local_language,
                labels=labels,
                local_labels=local_labels,
                use_local_labels=use_local_labels,
            )
        except Exception as exc:
            logger.warning(
                "Weasy bilingual receipt rendering failed for %s receipt; trying shaped Pillow fallback: %s",
                local_language,
                exc,
                exc_info=True,
            )
        try:
            return _build_receipt_pdf_bytes_pillow(
                payload,
                local_language=local_language,
                labels=labels,
                local_labels=local_labels,
                use_local_labels=use_local_labels,
            )
        except Exception as exc:
            logger.warning(
                "Pillow bilingual receipt rendering failed for %s receipt; falling back to ReportLab with bundled fonts: %s",
                local_language,
                exc,
                exc_info=True,
            )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A5,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
    )

    styles = getSampleStyleSheet()
    header_title = ParagraphStyle(
        "ReceiptHeaderTitle",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=11.5,
        leading=13,
        alignment=1,
        spaceAfter=1,
    )
    header_line = ParagraphStyle(
        "ReceiptHeaderLine",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.5,
        leading=10,
        alignment=1,
    )
    table_cell = ParagraphStyle(
        "ReceiptTableCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=11,
    )
    table_cell_small = ParagraphStyle(
        "ReceiptTableCellSmall",
        parent=table_cell,
        fontSize=8.4,
        leading=10.2,
    )
    table_cell_bold = ParagraphStyle(
        "ReceiptTableCellBold",
        parent=table_cell,
        fontName=f"{font_name}-Bold" if font_name == "Helvetica" else font_name,
    )
    table_cell_center = ParagraphStyle("ReceiptTableCellCenter", parent=table_cell, alignment=1)
    table_cell_right = ParagraphStyle("ReceiptTableCellRight", parent=table_cell, alignment=2)
    table_cell_small_right = ParagraphStyle("ReceiptTableCellSmallRight", parent=table_cell_small, alignment=2)
    footer_note = ParagraphStyle(
        "ReceiptFooterNote",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=7.8,
        leading=9.2,
        alignment=1,
    )
    powered_by_note = ParagraphStyle(
        "ReceiptPoweredByNote",
        parent=footer_note,
        fontSize=6.6,
        leading=8,
        alignment=2,
    )

    elements: list[Any] = []

    logo_obj = None
    logo_source = payload.get("logo")
    if logo_source:
        try:
            logo_obj = Image(logo_source, width=16 * mm, height=16 * mm)
        except Exception:
            logo_obj = None

    trust_name = _as_text(payload.get("trust_name"))
    temple_name = _as_text(payload.get("temple_name"), "Temple")
    primary_header = trust_name or temple_name
    secondary_header = temple_name if trust_name and temple_name and trust_name != temple_name else ""

    header_lines: list[Any] = []
    header_local_line = _as_text(payload.get("header_local_line"))
    if header_local_line and use_local_labels:
        header_lines.append(_receipt_paragraph(header_local_line, header_line))
    header_lines.append(_receipt_paragraph(primary_header, header_title))
    if secondary_header:
        header_lines.append(_receipt_paragraph(secondary_header, header_line))

    address_line = " ".join(
        part
        for part in [
            _as_text(payload.get("address")),
            _as_text(payload.get("city")),
            _as_text(payload.get("state")),
            _as_text(payload.get("pincode")),
        ]
        if part
    )
    if address_line:
        header_lines.append(_receipt_paragraph(address_line, header_line))
    if _as_text(payload.get("website")):
        header_lines.append(_receipt_paragraph(_as_text(payload.get("website")), header_line))
    if _as_text(payload.get("email")):
        header_lines.append(_receipt_paragraph(_as_text(payload.get("email")), header_line))
    if _as_text(payload.get("phone")):
        header_lines.append(_receipt_paragraph(f"Phone : {_as_text(payload.get('phone'))}", header_line))

    if logo_obj:
        logo_width = 22 * mm
        header_table = Table([[logo_obj, header_lines]], colWidths=[logo_width, doc.width - logo_width])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        elements.append(header_table)
    else:
        elements.extend(header_lines)

    elements.append(Spacer(1, 4))

    line_items = payload.get("line_items") or []
    if not line_items:
        line_items = [{"description": "-", "amount": payload.get("total_amount", 0)}]

    total_amount = payload.get("total_amount")
    if total_amount is None:
        total_amount = sum(_safe_float(item.get("amount"), 0.0) for item in line_items)

    receipt_title_raw = _as_text(payload.get("receipt_title"))
    receipt_title_local = _as_text(payload.get("receipt_title_local")) or local_labels.get("receipt_title", "")
    receipt_title = _bilingual_label(receipt_title_local, receipt_title_raw, use_local_labels) if receipt_title_raw else labels["receipt_title"]
    receipt_no_label = _as_text(payload.get("receipt_number_label")) or labels["receipt_number"]
    date_label = _as_text(payload.get("date_label")) or labels["date"]
    party_label_raw = payload.get("party_label")
    party_label = labels["party"] if party_label_raw is None else _as_text(party_label_raw, "")
    if _normalize_local_language(local_language) == "kannada" and payload.get("receipt_title") == "Donation Receipt":
        party_label = _bilingual_label(local_labels.get("donation_party", ""), "Donor", use_local_labels)
    address_label = _as_text(payload.get("address_label")) or labels["address"]
    line_item_header_raw = _as_text(payload.get("line_item_header"))
    line_item_local = _as_text(payload.get("line_item_local")) or local_labels.get("line_item", "")
    line_item_header = _bilingual_label(line_item_local, line_item_header_raw, use_local_labels) if line_item_header_raw else labels["line_item"]
    total_label = _as_text(payload.get("total_label")) or labels["total"]
    gotra_label = _as_text(payload.get("gotra_label")) or labels["gotra"]
    star_label = _as_text(payload.get("nakshatra_label")) or labels["nakshatra"]
    rashi_label = _as_text(payload.get("rashi_label")) or labels["rashi"]
    service_date_label_raw = _as_text(payload.get("service_date_label"))
    service_date_local = _as_text(payload.get("service_date_local")) or local_labels.get("service_date", "")
    service_date_label = _bilingual_label(service_date_local, service_date_label_raw, use_local_labels) if service_date_label_raw else labels["service_date"]
    signatory_label = _as_text(payload.get("signatory_label"), labels["cashier"])

    rows: list[list[Any]] = []
    rows.append([_receipt_paragraph(receipt_title, table_cell_center), "", ""])
    rows.append([
        _receipt_paragraph(f"{receipt_no_label}: {_as_text(payload.get('receipt_number'), '-')}", table_cell_small),
        _receipt_paragraph(f"{date_label}: {_as_text(payload.get('receipt_date'), '-')}", table_cell_small_right),
        "",
    ])
    party_name = _as_text(payload.get("party_name"), "-")
    party_line = f"{party_label}: {party_name}" if party_label else party_name
    rows.append([_receipt_paragraph(party_line, table_cell), "", ""])
    rows.append([_receipt_paragraph(f"{address_label}: {_as_text(payload.get('address_value'), '--')}", table_cell), "", ""])
    rows.append([_receipt_paragraph(_as_text(payload.get('amount_words_line'), 'Received with thanks'), table_cell_small), "", ""])
    rows.append([_receipt_paragraph(_as_text(payload.get('payment_line'), 'Received with thanks.'), table_cell_small), "", ""])

    rows.append([
        _receipt_paragraph(line_item_header, table_cell_bold),
        _receipt_paragraph('Rs', table_cell_center),
        _receipt_paragraph('', table_cell_center),
    ])

    for item in line_items:
        major, minor = _split_amount(item.get('amount'))
        rows.append([
            _receipt_paragraph(_as_text(item.get('description'), '-'), table_cell),
            _receipt_paragraph(major, table_cell_right),
            _receipt_paragraph(minor, table_cell_right),
        ])

    total_major, total_minor = _split_amount(total_amount)
    rows.append([
        _receipt_paragraph(total_label, table_cell_right),
        _receipt_paragraph(total_major, table_cell_right),
        _receipt_paragraph(total_minor, table_cell_right),
    ])

    include_note_row = bool(payload.get("include_note_row", True))
    if include_note_row:
        note_line_local = _as_text(payload.get('note_local'), labels['note_local'])
        note_line_english = _as_text(payload.get('note_english'), '')
        note_lines = [line for line in [note_line_local if use_local_labels else '', note_line_english] if line]
        note_block = '\n'.join(note_lines)
        rows.append([_receipt_paragraph(note_block or '-', table_cell_center), '', ''])

    col1 = doc.width * 0.72
    col2 = doc.width * 0.20
    col3 = doc.width - col1 - col2
    table = Table(rows, colWidths=[col1, col2, col3])

    note_row_index = len(rows) - 1 if include_note_row else None
    table_style = [
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#808080')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A0A0A0')),
        ('SPAN', (0, 0), (2, 0)),
        ('SPAN', (1, 1), (2, 1)),
        ('SPAN', (0, 2), (2, 2)),
        ('SPAN', (0, 3), (2, 3)),
        ('SPAN', (0, 4), (2, 4)),
        ('SPAN', (0, 5), (2, 5)),
        ('BACKGROUND', (0, 0), (2, 0), colors.HexColor('#F2F2F2')),
        ('BACKGROUND', (0, 6), (2, 6), colors.HexColor('#F8F8F8')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 2), (2, 5), 4),
        ('BOTTOMPADDING', (0, 2), (2, 5), 4),
        ('LEFTPADDING', (0, 2), (0, 5), 6),
        ('TOPPADDING', (0, 6), (2, 6), 4),
        ('BOTTOMPADDING', (0, 6), (2, 6), 4),
    ]
    if note_row_index is not None:
        table_style.extend([
            ('SPAN', (0, note_row_index), (2, note_row_index)),
            ('BACKGROUND', (0, note_row_index), (2, note_row_index), colors.HexColor('#F8F8F8')),
            ('BOTTOMPADDING', (0, note_row_index), (2, note_row_index), 5),
        ])
    table.setStyle(TableStyle(table_style))

    elements.append(table)
    elements.append(Spacer(1, 4))

    if bool(payload.get('include_astro_row', True)):
        astro_line = (
            f"{gotra_label}: {_as_text(payload.get('gotra'), '--')}    "
            f"{star_label}: {_as_text(payload.get('nakshatra'), '--')}    "
            f"{rashi_label}: {_as_text(payload.get('rashi'), '--')}"
        )
        elements.append(_receipt_paragraph(astro_line, table_cell_small))
        elements.append(Spacer(1, 2))

    if bool(payload.get('include_service_row', True)):
        service_line = f"{service_date_label}: {_as_text(payload.get('service_date'), '--')}"
        elements.append(_receipt_paragraph(service_line, table_cell_small))
        elements.append(Spacer(1, 2))

    system_line_raw = payload.get('system_generated_line')
    if system_line_raw is None:
        system_line = 'This is a system generated receipt and does not require any signature.'
    else:
        system_line = str(system_line_raw).strip()

    powered_by = _as_text(payload.get('powered_by_line'), 'Powered by Sanmitra Tech Solutions.')

    if system_line:
        elements.append(_receipt_paragraph(system_line, footer_note))
        elements.append(Spacer(1, 4))
    elements.append(_receipt_paragraph(powered_by, powered_by_note))

    doc.build(elements)
    return buffer.getvalue()

