"""Mechanical extraction for mandir_compat batch 8 (shared helpers only).

Extracts non-quarantine helpers from router.py into helpers/*.py.
Does NOT move receipt-number sequencing, posting/cancellation core, or panchang.
Run: python scripts/extract_mandir_batch8.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"
HELPERS = ROOT / "app/modules/mandir_compat/helpers"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


HELPER_FOOTER = '''
# Shared helpers moved to helpers/*.py (batch 8); re-exported for route modules and tests.
from app.modules.mandir_compat.helpers.coercions import (
    _normalize_phone as _normalize_phone,
    _parse_iso_datetime as _parse_iso_datetime,
    _parse_opening_balance_decimal as _parse_opening_balance_decimal,
    _safe_bool as _safe_bool,
    _safe_float as _safe_float,
    _safe_optional_float as _safe_optional_float,
    _safe_optional_int as _safe_optional_int,
    _safe_optional_str as _safe_optional_str,
)
from app.modules.mandir_compat.helpers.opening_balance import (
    _current_opening_balance_net as _current_opening_balance_net,
    _find_or_create_opening_balance_offset_account as _find_or_create_opening_balance_offset_account,
    _parse_opening_balance_rows as _parse_opening_balance_rows,
)
from app.modules.mandir_compat.helpers.mongo_utils import (
    _sanitize_mongo_doc as _sanitize_mongo_doc,
)
from app.modules.mandir_compat.helpers.views import (
    _mandir_donation_view as _mandir_donation_view,
    _mandir_filter_rows as _mandir_filter_rows,
    _mandir_row_date_text as _mandir_row_date_text,
    _mandir_row_matches_search as _mandir_row_matches_search,
    _mandir_seva_booking_view as _mandir_seva_booking_view,
    _receipt_number_for_donation as _receipt_number_for_donation,
    _receipt_number_for_seva as _receipt_number_for_seva,
)
from app.modules.mandir_compat.helpers.pincode import (
    MANDIR_PINCODE_FALLBACKS as MANDIR_PINCODE_FALLBACKS,
    _lookup_pincode_city_state as _lookup_pincode_city_state,
    _normalize_pincode as _normalize_pincode,
    _to_positive_int as _to_positive_int,
)
from app.modules.mandir_compat.helpers.seva_booking import (
    _compute_seva_available_today as _compute_seva_available_today,
    _count_seva_bookings_for_date as _count_seva_bookings_for_date,
    _normalize_seva_availability as _normalize_seva_availability,
    _normalize_seva_category as _normalize_seva_category,
    _normalize_seva_day as _normalize_seva_day,
    _parse_booking_date as _parse_booking_date,
    _resolve_export_window as _resolve_export_window,
    _resolve_report_date_window as _resolve_report_date_window,
    _today_weekday_js_index as _today_weekday_js_index,
    _validate_seva_booking_capacity as _validate_seva_booking_capacity,
    _validate_seva_booking_date as _validate_seva_booking_date,
    _weekday_js_index_for_date as _weekday_js_index_for_date,
)
from app.modules.mandir_compat.helpers.seva_builders import (
    _build_seva_item as _build_seva_item,
    _build_seva_patch as _build_seva_patch,
    _canonical_seva_name as _canonical_seva_name,
    _dashboard_posted_stats as _dashboard_posted_stats,
    _seva_import_template_csv as _seva_import_template_csv,
    _serialize_seva_doc as _serialize_seva_doc,
)
from app.modules.mandir_compat.helpers.devotees_upi import (
    _build_upi_intent_uri as _build_upi_intent_uri,
    _find_devotee_by_phone as _find_devotee_by_phone,
    _mandir_upi_payment_view as _mandir_upi_payment_view,
    _upi_receipt_number as _upi_receipt_number,
    _upsert_devotee_from_contribution as _upsert_devotee_from_contribution,
)
from app.modules.mandir_compat.helpers.tenant_platform import (
    _assert_platform_can_write_tenant as _assert_platform_can_write_tenant,
    _is_platform_super_admin as _is_platform_super_admin,
    _payment_accounts as _payment_accounts,
    _resolve_tenant_for_mandir_request as _resolve_tenant_for_mandir_request,
)

'''


def write_helpers(lines: list[str]) -> None:
    coercions_body = (
        slice_lines(lines, 683, 746)
        + slice_lines(lines, 1619, 1635)
    )
    opening_body = slice_lines(lines, 754, 861)
    mongo_body = slice_lines(lines, 865, 869)
    views_body = (
        slice_lines(lines, 955, 964)
        + slice_lines(lines, 973, 1028)
        + slice_lines(lines, 1050, 1072)
    )
    pincode_body = slice_lines(lines, 1080, 1139)
    seva_booking_body = (
        slice_lines(lines, 1142, 1158)
        + slice_lines(lines, 1167, 1375)
    )
    seva_builders_body = slice_lines(lines, 1382, 1617)
    devotees_body = slice_lines(lines, 1643, 1893)
    tenant_body = slice_lines(lines, 1902, 1983)

    (HELPERS / "coercions.py").write_text(
        f'''"""MandirMitra safe type coercions and phone/datetime helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

{coercions_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "opening_balance.py").write_text(
        f'''"""MandirMitra opening balance import helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account, JournalEntry, JournalLine
from app.accounting.service import create_account
from app.modules.mandir_compat.helpers.coercions import _parse_opening_balance_decimal

{opening_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "mongo_utils.py").write_text(
        f'''"""MandirMitra MongoDB document sanitization helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

{mongo_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "views.py").write_text(
        f'''"""MandirMitra donation/seva list view and row-filter helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.modules.mandir_compat.donation_compliance import compliance_public_fields
from app.modules.mandir_compat.helpers.mongo_utils import _sanitize_mongo_doc

{views_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "pincode.py").write_text(
        f'''"""MandirMitra pincode lookup helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.modules.mandir_compat.helpers.coercions import _safe_optional_int

{pincode_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "seva_booking.py").write_text(
        f'''"""MandirMitra seva booking validation and date-window helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers.coercions import (
    _safe_bool,
    _safe_optional_int,
)

{seva_booking_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "seva_builders.py").write_text(
        f'''"""MandirMitra seva CRUD builders and dashboard stats helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mandir_compat.helpers.coercions import (
    _safe_bool,
    _safe_float,
    _safe_optional_float,
    _safe_optional_int,
    _safe_optional_str,
)
from app.modules.mandir_compat.helpers.seva_booking import (
    _compute_seva_available_today,
    _normalize_seva_availability,
    _normalize_seva_category,
    _normalize_seva_day,
)
from app.modules.mandir_compat.report_helpers import posted_donations, posted_sevas

logger = logging.getLogger(__name__)

{seva_builders_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "devotees_upi.py").write_text(
        f'''"""MandirMitra devotee lookup/upsert and UPI payment view helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers.coercions import (
    _normalize_phone,
    _safe_float,
)
from app.modules.mandir_compat.helpers.mongo_utils import _sanitize_mongo_doc

{devotees_body}
''',
        encoding="utf-8",
    )

    (HELPERS / "tenant_platform.py").write_text(
        f'''"""MandirMitra platform admin and payment-account resolver helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.tenants.context import resolve_tenant_id
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.service import resolve_tenant_by_temple_id

{tenant_body}
''',
        encoding="utf-8",
    )


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 677),
        (
            "# Safe coercions, opening balance, mongo, views, pincode, seva, devotee/UPI, and\n"
            "# tenant helpers moved to helpers/*.py; re-exported at end of module.\n\n"
        ),
        slice_lines(lines, 873, 954),
        (
            "\n# Donation/seva view helpers moved to helpers/views.py\n\n"
        ),
        slice_lines(lines, 1991, 2033),
        slice_lines(lines, 2037, len(lines)),
    ]
    text = "".join(chunks)
    anchor = "from app.modules.mandir_compat.helpers.legacy_coa import"
    if anchor not in text:
        raise RuntimeError(f"Expected anchor not found: {anchor}")
    text = text.replace(anchor, HELPER_FOOTER + anchor, 1)
    return text


def main() -> None:
    lines = read_lines()
    original = len(lines)
    write_helpers(lines)
    ROUTER.write_text(rewrite_router(lines), encoding="utf-8")
    print(f"router.py: {original} -> {len(ROUTER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
