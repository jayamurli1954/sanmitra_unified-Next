"""Mechanical extraction for mandir_compat batch 4 (no panchang).

Extracts seva routes, temple routes, accounts routes, legacy COA helpers,
and account seeding helpers. Run: python scripts/extract_mandir_batch4.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def apply_replacements(body: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        body = body.replace(old, new)
    return body


ROUTE_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("_sanitize_mongo_doc(", "mandir_router._sanitize_mongo_doc("),
    ("resolve_app_key(", "mandir_router.resolve_app_key("),
    ("resolve_tenant_id(", "mandir_router.resolve_tenant_id("),
    ("await _resolve_tenant_for_mandir_request(", "await mandir_router._resolve_tenant_for_mandir_request("),
    ("await _assert_platform_can_write_tenant(", "await mandir_router._assert_platform_can_write_tenant("),
    ("await _ensure_default_mandir_accounts(", "await mandir_router._ensure_default_mandir_accounts("),
    ("await _upsert_mandir_account_docs(", "await mandir_router._upsert_mandir_account_docs("),
    ("await _sync_mandir_sql_accounts_from_seed(", "await mandir_router._sync_mandir_sql_accounts_from_seed("),
    ("await _normalize_mandir_income_accounts(", "await mandir_router._normalize_mandir_income_accounts("),
    ("await _payment_accounts(", "await mandir_router._payment_accounts("),
    ("await ensure_temple_numeric_id(", "await mandir_router.ensure_temple_numeric_id("),
    ("_normalize_mandir_account_code(", "mandir_router._normalize_mandir_account_code("),
    ("_normalize_public_donation_categories(", "mandir_router._normalize_public_donation_categories("),
    ("_load_mandir_legacy_accounts(", "mandir_router._load_mandir_legacy_accounts("),
    ("_mandir_seed_accounts(", "mandir_router._mandir_seed_accounts("),
    ("_dedupe_mandir_account_docs(", "mandir_router._dedupe_mandir_account_docs("),
    ("_mandir_account_view(", "mandir_router._mandir_account_view("),
    ("_serialize_seva_doc(", "mandir_router._serialize_seva_doc("),
    ("_parse_booking_date(", "mandir_router._parse_booking_date("),
    ("_validate_seva_booking_date(", "mandir_router._validate_seva_booking_date("),
    ("await _validate_seva_booking_capacity(", "await mandir_router._validate_seva_booking_capacity("),
    ("_build_seva_item(", "mandir_router._build_seva_item("),
    ("_build_seva_patch(", "mandir_router._build_seva_patch("),
    ("_seva_import_template_csv(", "mandir_router._seva_import_template_csv("),
    ("_safe_optional_float(", "mandir_router._safe_optional_float("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_to_positive_int(", "mandir_router._to_positive_int("),
    ("logger.", "mandir_router.logger."),
]

LEGACY_COA_REPLACEMENTS = [
    ("get_collection(", "mandir_router.get_collection("),
    ("_safe_optional_str(", "mandir_router._safe_optional_str("),
    ("_safe_bool(", "mandir_router._safe_bool("),
]

SEEDING_REPLACEMENTS = [
    ("_load_mandir_legacy_accounts()", "_legacy_coa._load_mandir_legacy_accounts()"),
    ("_prepare_mandir_account_docs(", "_legacy_coa._prepare_mandir_account_docs("),
    ("_upsert_mandir_account_docs(", "_legacy_coa._upsert_mandir_account_docs("),
    ("_normalize_mandir_account_code(", "mandir_router._normalize_mandir_account_code("),
    ("await _normalize_mandir_income_accounts(", "await mandir_router._normalize_mandir_income_accounts("),
    ("await create_account(", "await mandir_router.create_account("),
    ("await list_accounts(", "await mandir_router.list_accounts("),
    ("logger.", "mandir_router.logger."),
]


def write_modules(lines: list[str]) -> None:
    legacy_body = apply_replacements(slice_lines(lines, 1183, 1342), LEGACY_COA_REPLACEMENTS)
    seeding_body = apply_replacements(
        slice_lines(lines, 675, 748) + slice_lines(lines, 757, 988),
        SEEDING_REPLACEMENTS,
    )
    sevas_body = apply_replacements(slice_lines(lines, 3247, 3553), ROUTE_REPLACEMENTS)
    temples_body = apply_replacements(slice_lines(lines, 3561, 3626), ROUTE_REPLACEMENTS)
    accounts_body = apply_replacements(slice_lines(lines, 3640, 3840), ROUTE_REPLACEMENTS)

    helpers_dir = ROOT / "app/modules/mandir_compat/helpers"
    helpers_dir.mkdir(parents=True, exist_ok=True)
    routes_dir = ROOT / "app/modules/mandir_compat/routes"

    (helpers_dir / "legacy_coa.py").write_text(
        f'''"""MandirMitra legacy chart-of-accounts import helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.modules.mandir_compat import router as mandir_router

MANDIR_COMPAT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANDIR_LEGACY_COA_PATH = MANDIR_COMPAT_DATA_DIR / "legacy_mandir_coa.json"

{legacy_body}
''',
        encoding="utf-8",
    )

    (helpers_dir / "account_seeding.py").write_text(
        f'''"""MandirMitra account seeding and SQL COA sync helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers import legacy_coa as _legacy_coa

{seeding_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "sevas.py").write_text(
        f'''"""MandirMitra seva master CRUD and import routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from fastapi import Depends, File, Header, HTTPException, Query, Response, UploadFile

from app.core.auth.dependencies import get_current_user
from app.core.tenants.app_resolvers import resolve_mandir_tenant
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import (
    _MANDIR_ADMIN_ROUTE_DEPS,
    _MANDIR_WRITE_ROUTE_DEPS,
    router,
)

{sevas_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "temples.py").write_text(
        f'''"""MandirMitra current-temple profile routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, Query

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router

{temples_body}
''',
        encoding="utf-8",
    )

    (routes_dir / "accounts.py").write_text(
        f'''"""MandirMitra chart-of-accounts list, edit, and import routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.core.audit.service import log_audit_event
from app.core.auth.dependencies import get_current_user
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router


def _ok(name: str, **extra: Any) -> dict[str, Any]:
    return {{"status": "ok", "endpoint": name, **extra}}


{accounts_body}
''',
        encoding="utf-8",
    )


FOOTER = '''
from app.modules.mandir_compat.helpers.legacy_coa import (
    _coerce_account_id as _coerce_account_id,
    _infer_cash_bank_nature as _infer_cash_bank_nature,
    _infer_flag as _infer_flag,
    _load_mandir_legacy_accounts as _load_mandir_legacy_accounts,
    _prepare_mandir_account_docs as _prepare_mandir_account_docs,
    _upsert_mandir_account_docs as _upsert_mandir_account_docs,
)
from app.modules.mandir_compat.helpers.account_seeding import (
    MANDIR_DEFAULT_ACCOUNTS as MANDIR_DEFAULT_ACCOUNTS,
    _dedupe_mandir_account_docs as _dedupe_mandir_account_docs,
    _ensure_default_mandir_accounts as _ensure_default_mandir_accounts,
    _ensure_default_mandir_sql_accounts as _ensure_default_mandir_sql_accounts,
    _ensure_default_mandir_sql_accounts_safe as _ensure_default_mandir_sql_accounts_safe,
    _mandir_account_view as _mandir_account_view,
    _mandir_seed_accounts as _mandir_seed_accounts,
    _sync_mandir_sql_accounts_from_seed as _sync_mandir_sql_accounts_from_seed,
)

import app.modules.mandir_compat.routes.sevas  # noqa: E402, F401
import app.modules.mandir_compat.routes.temples  # noqa: E402, F401
import app.modules.mandir_compat.routes.accounts  # noqa: E402, F401
from app.modules.mandir_compat.routes.sevas import (
    create_seva as create_seva,
    delete_seva as delete_seva,
    import_sevas as import_sevas,
    list_sevas as list_sevas,
    seva_date_availability as seva_date_availability,
    seva_dropdown_options as seva_dropdown_options,
    seva_import_template as seva_import_template,
    seva_payment_accounts as seva_payment_accounts,
    seva_priests as seva_priests,
    update_seva as update_seva,
)
from app.modules.mandir_compat.routes.temples import (
    get_current_temple as get_current_temple,
    update_current_temple as update_current_temple,
)
from app.modules.mandir_compat.routes.accounts import (
    mandir_accounts_hierarchy as mandir_accounts_hierarchy,
    mandir_accounts_import_legacy as mandir_accounts_import_legacy,
    mandir_accounts_initialize_default as mandir_accounts_initialize_default,
    mandir_accounts_list as mandir_accounts_list,
    mandir_accounts_update as mandir_accounts_update,
)

'''


def rewrite_router(lines: list[str]) -> str:
    chunks = [
        slice_lines(lines, 1, 674),
        (
            "# Default COA seed + legacy import helpers moved to helpers/*.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); re-exported at end of module.\n\n"
        ),
        slice_lines(lines, 991, 1175),
        "# Legacy COA import helpers moved to helpers/legacy_coa.py\n\n",
        slice_lines(lines, 1345, 3246),
        (
            "# Seva routes moved to routes/sevas.py\n"
            "# (docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md); registered via import at end of module.\n\n"
            "# Temple routes moved to routes/temples.py\n\n"
            "# Accounts / COA routes moved to routes/accounts.py\n\n"
        ),
        slice_lines(lines, 3845, len(lines)),
    ]
    text = "".join(chunks)
    text = text.replace(
        "# SECTION: DONATION RECEIPT PDF (ReportLab)\n"
        "# NOTE   : moved to receipt_pdf.py; re-exported at end of module.\n"
        "# ════════════════════════════════════════════════════════════════════════\n\n"
        "# ════════════════════════════════════════════════════════════════════════\n"
        "# SECTION: DONATION RECEIPT PDF (ReportLab)\n"
        "# NOTE   : PDF builders moved to receipt_pdf.py; re-exported at end of module.\n"
        "# SECTION: SEVA RECEIPT PDF (ReportLab) + SEVA BOOKING VIEW\n"
        "# NOTE   : _receipt_number_for_seva and _mandir_seva_booking_view remain below.\n"
        "# ════════════════════════════════════════════════════════════════════════\n\n",
        "# SECTION: DONATION RECEIPT PDF (ReportLab)\n"
        "# NOTE   : moved to receipt_pdf.py; re-exported at end of module.\n"
        "# SECTION: SEVA RECEIPT PDF (ReportLab) + SEVA BOOKING VIEW\n"
        "# NOTE   : _receipt_number_for_seva and _mandir_seva_booking_view remain below.\n"
        "# ════════════════════════════════════════════════════════════════════════\n\n",
    )
    anchor = "import app.modules.mandir_compat.routes.dashboard"
    if anchor in text:
        text = text.replace(anchor, FOOTER + anchor, 1)
    else:
        text = text.rstrip() + FOOTER
    return text


def main() -> None:
    lines = read_lines()
    original = len(lines)
    write_modules(lines)
    ROUTER.write_text(rewrite_router(lines), encoding="utf-8")
    print(f"router.py: {original} -> {len(ROUTER.read_text(encoding='utf-8').splitlines())} lines")


if __name__ == "__main__":
    main()
