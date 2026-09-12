"""One-off mechanical extraction for mandir_compat batch 3 (no panchang).

Pure move: copies line ranges verbatim into new modules and rewrites router.py.
Run from repo root: python scripts/extract_mandir_batch3.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    """1-based inclusive start/end."""
    return "".join(lines[start - 1 : end])


def patch_mandir_calls(body: str) -> str:
    replacements = [
        ("get_collection(", "mandir_router.get_collection("),
        ("_sanitize_mongo_doc(", "mandir_router._sanitize_mongo_doc("),
        ("_mandir_actor_id(", "mandir_router._mandir_actor_id("),
        ("await _ensure_default_mandir_sql_accounts_safe(", "await mandir_router._ensure_default_mandir_sql_accounts_safe("),
        ("await _resolve_or_create_mandir_account(", "await mandir_router._resolve_or_create_mandir_account("),
        ("await _reverse_mandir_source_journal(", "await mandir_router._reverse_mandir_source_journal("),
        ("await _mandir_fund_subledger_data(", "await mandir_router._mandir_fund_subledger_data("),
    ]
    for old, new in replacements:
        body = body.replace(old, new)
    return body


def write_auxiliary_modules(lines: list[str]) -> None:
    account_body = slice_lines(lines, 148, 148) + slice_lines(lines, 207, 336)
    funds_only = patch_mandir_calls(slice_lines(lines, 4509, 4940))
    festivals_body = patch_mandir_calls(slice_lines(lines, 4942, 4986))
    receipt_parts = [
        slice_lines(lines, 1630, 1694),
        slice_lines(lines, 1727, 1797),
        slice_lines(lines, 1800, 3512),
    ]
    receipt_body = "".join(receipt_parts)

    helpers_dir = ROOT / "app/modules/mandir_compat/helpers"
    helpers_dir.mkdir(parents=True, exist_ok=True)
    (helpers_dir / "__init__.py").write_text('"""MandirMitra helper modules."""\n', encoding="utf-8")

    account_categories = f'''"""MandirMitra account code and income category helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

{account_body}
'''
    (helpers_dir / "account_categories.py").write_text(account_categories, encoding="utf-8")

    funds_module = f'''"""MandirMitra fund master, transfers, and opening balance routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import post_journal_entry, reverse_journal_entry
from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.db.postgres import get_async_session
from app.modules.business.dimensions import create_dimension, deactivate_dimension
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

logger = logging.getLogger(__name__)

{funds_only}
'''
    (ROOT / "app/modules/mandir_compat/routes/funds.py").write_text(funds_module, encoding="utf-8")

    festivals_module = f'''"""MandirMitra festival master routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import Depends, Header, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

{festivals_body}
'''
    (ROOT / "app/modules/mandir_compat/routes/festivals.py").write_text(festivals_module, encoding="utf-8")

    receipt_module = f'''"""MandirMitra donation and seva receipt PDF rendering.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Rendering only; posting and
sequence numbering remain in router.py.
"""
from __future__ import annotations

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


def _safe_float(value: Any, default: float = 0.0) -> float:
    return mandir_router._safe_float(value, default)


def _receipt_number_for_donation(donation: dict[str, Any]) -> str:
    return mandir_router._receipt_number_for_donation(donation)


def _receipt_number_for_seva(doc: dict[str, Any]) -> str:
    return mandir_router._receipt_number_for_seva(doc)


{receipt_body}
'''
    (ROOT / "app/modules/mandir_compat/receipt_pdf.py").write_text(receipt_module, encoding="utf-8")


ACCOUNT_IMPORT = '''
from app.modules.mandir_compat.helpers.account_categories import (
    _MANDIR_INCOME_BUCKET_ALIASES,
    _MANDIR_INCOME_LEGACY_CODES,
    _MANDIR_LEGACY_ACCOUNT_CODE_MAP,
    _MANDIR_SPONSORSHIP_CATEGORY_MARKERS,
    _MANDIR_UTR_REFERENCE_PATTERN,
    _is_mandir_sponsorship_category,
    _mandir_cash_income_category,
    _mandir_in_kind_debit_account_target,
    _mandir_in_kind_income_category,
    _mandir_income_bucket_for_account,
    _normalize_income_category,
    _normalize_mandir_account_code,
    _normalize_public_payment_utr_reference,
)
'''

ACCOUNT_STUB = '''
# ════════════════════════════════════════════════════════════════════════
# SECTION: ACCOUNT CODE + CATEGORY HELPERS
# NOTE   : moved to helpers/account_categories.py; imported above.
# ════════════════════════════════════════════════════════════════════════

'''

RECEIPT_STUB = '''
# ════════════════════════════════════════════════════════════════════════
# SECTION: DONATION RECEIPT PDF (ReportLab)
# NOTE   : PDF builders moved to receipt_pdf.py; re-exported at end of module.
# SECTION: SEVA RECEIPT PDF (ReportLab) + SEVA BOOKING VIEW
# NOTE   : _receipt_number_for_seva and _mandir_seva_booking_view remain below.
# ════════════════════════════════════════════════════════════════════════

'''

FUNDS_STUB = '''
# Fund and festival routes moved to routes/funds.py and routes/festivals.py
# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.

'''

RECEIPT_REEXPORT = '''
from app.modules.mandir_compat.receipt_pdf import (
    _amount_to_kannada_words as _amount_to_kannada_words,
    _amount_to_words as _amount_to_words,
    _amount_words_receipt_line as _amount_words_receipt_line,
    _as_text as _as_text,
    _bilingual_label as _bilingual_label,
    _build_receipt_pdf_bytes as _build_receipt_pdf_bytes,
    _build_receipt_pdf_bytes_pillow as _build_receipt_pdf_bytes_pillow,
    _build_receipt_pdf_bytes_weasy as _build_receipt_pdf_bytes_weasy,
    _build_temple_receipt_profile as _build_temple_receipt_profile,
    _compose_receipt_address_line as _compose_receipt_address_line,
    _compose_receipt_line_description as _compose_receipt_line_description,
    _compose_receipt_party_name as _compose_receipt_party_name,
    _default_labels as _default_labels,
    _detect_script as _detect_script,
    _extract_seva_line_items as _extract_seva_line_items,
    _first_non_empty_text as _first_non_empty_text,
    _format_payment_mode_for_receipt as _format_payment_mode_for_receipt,
    _format_payment_mode_local_for_receipt as _format_payment_mode_local_for_receipt,
    _format_receipt_date as _format_receipt_date,
    _generate_donation_receipt_pdf_bytes as _generate_donation_receipt_pdf_bytes,
    _generate_seva_receipt_pdf_bytes as _generate_seva_receipt_pdf_bytes,
    _integer_to_kannada_words as _integer_to_kannada_words,
    _integer_to_words as _integer_to_words,
    _name_prefix_from_sources as _name_prefix_from_sources,
    _normalize_local_language as _normalize_local_language,
    _receipt_paragraph as _receipt_paragraph,
    _receipt_payment_line as _receipt_payment_line,
    _resolve_font_name as _resolve_font_name,
    _resolve_temple_receipt_profile as _resolve_temple_receipt_profile,
    _split_amount as _split_amount,
)

import app.modules.mandir_compat.routes.funds  # noqa: E402, F401
import app.modules.mandir_compat.routes.festivals  # noqa: E402, F401
'''


def rewrite_router(lines: list[str]) -> str:
    seva_view = slice_lines(lines, 1698, 1724)  # section header + seva view helpers
    chunks = [
        slice_lines(lines, 1, 147),  # through receipt prefix constants
        slice_lines(lines, 149, 206),  # skip UTR pattern line 148
        ACCOUNT_IMPORT,
        ACCOUNT_STUB,
        slice_lines(lines, 341, 1629),  # async resolvers through row filtering
        RECEIPT_STUB,
        seva_view,
        slice_lines(lines, 3513, 4508),  # pincode through donation categories
        FUNDS_STUB,
        slice_lines(lines, 4987, len(lines)),  # donations route onward
    ]
    text = "".join(chunks)
    text = text.replace(
        "import app.modules.mandir_compat.routes.dashboard",
        RECEIPT_REEXPORT + "\nimport app.modules.mandir_compat.routes.dashboard",
        1,
    )
    if "import app.modules.mandir_compat.routes.funds" not in text:
        text = text.rstrip() + RECEIPT_REEXPORT
    return text


def main() -> None:
    lines = read_lines()
    original_count = len(lines)
    write_auxiliary_modules(lines)
    new_text = rewrite_router(lines)
    ROUTER.write_text(new_text, encoding="utf-8")
    new_count = len(new_text.splitlines())
    print(f"router.py: {original_count} -> {new_count} lines")
    print("Wrote helpers/account_categories.py, routes/funds.py, routes/festivals.py, receipt_pdf.py")


if __name__ == "__main__":
    main()
