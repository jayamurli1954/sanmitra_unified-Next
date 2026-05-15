"""
Bulk regenerate MandirMitra receipt PDFs using the latest backend rendering logic.

This script reads donations/seva bookings from MongoDB and renders fresh PDFs
with current code fixes (fonts, dual-language handling, receipt layout, etc).
"""

from __future__ import annotations

import argparse
import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from app.db.mongo import close_mongo, get_collection, init_mongo
from app.modules.mandir_compat.router import (
    _build_temple_receipt_profile,
    _generate_donation_receipt_pdf_bytes,
    _generate_seva_receipt_pdf_bytes,
    _next_receipt_number,
    _normalize_local_language,
    _receipt_number_for_donation,
    _receipt_number_for_seva,
)

DONATION_NUMBER_RE = re.compile(r"^DON-\d{7}$")
SEVA_NUMBER_RE = re.compile(r"^SEV-\d{7}$")


def _safe_name(value: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in ("-", "_")).strip()
    return cleaned or fallback


def _strip_mongo_id(doc: dict[str, Any]) -> dict[str, Any]:
    row = dict(doc or {})
    row.pop("_id", None)
    return row


async def _resolve_temple_profile(tenant_id: str, app_key: str, lang_override: str | None) -> dict[str, Any]:
    temples = get_collection("mandir_temples")
    panchang = get_collection("mandir_panchang_settings")

    temple_doc = await temples.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    if not temple_doc:
        temple_doc = await temples.find_one({"tenant_id": tenant_id}) or {}
    temple_profile = _build_temple_receipt_profile(temple_doc)

    lang_doc = await panchang.find_one({"tenant_id": tenant_id, "app_key": app_key}) or {}
    selected_language = _normalize_local_language(
        lang_override
        or temple_doc.get("receipt_local_language")
        or lang_doc.get("receipt_local_language")
        or lang_doc.get("primary_language")
        or temple_doc.get("primary_language")
        or temple_profile.get("local_language")
    )
    if selected_language:
        temple_profile["local_language"] = selected_language
    return temple_profile


async def _regen_donations(
    *,
    tenant_id: str,
    app_key: str,
    output_dir: Path,
    limit: int,
    update_metadata: bool,
    renumber_existing: bool,
    temple_profile: dict[str, Any],
) -> int:
    donations_col = get_collection("mandir_donations")
    docs = await (
        donations_col.find({"tenant_id": tenant_id, "app_key": app_key})
        .sort("created_at", 1)
        .limit(limit)
        .to_list(length=limit)
    )

    target = output_dir / "donations"
    target.mkdir(parents=True, exist_ok=True)

    count = 0
    for doc in docs:
        row = _strip_mongo_id(doc)
        donation_id_text = str(row.get("donation_id") or row.get("id") or "").strip()
        if not donation_id_text:
            continue

        row["donation_id"] = donation_id_text
        row["id"] = donation_id_text
        receipt_number = _receipt_number_for_donation(row)
        if renumber_existing and not DONATION_NUMBER_RE.match(receipt_number):
            receipt_number = await _next_receipt_number(
                tenant_id=tenant_id,
                app_key=app_key,
                receipt_kind="donation",
                receipt_date=row.get("donation_date") or row.get("created_at"),
            )
        row["receipt_number"] = receipt_number
        row["receipt_pdf_url"] = f"/api/v1/donations/{donation_id_text}/receipt/pdf"

        pdf_bytes = _generate_donation_receipt_pdf_bytes(
            row,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
        file_name = f"donation_receipt_{_safe_name(row['receipt_number'], donation_id_text[:8])}.pdf"
        (target / file_name).write_bytes(pdf_bytes)
        count += 1

        if update_metadata:
            await donations_col.update_one(
                {"tenant_id": tenant_id, "app_key": app_key, "donation_id": donation_id_text},
                {
                    "$set": {
                        "id": donation_id_text,
                        "receipt_number": row["receipt_number"],
                        "receipt_pdf_url": row["receipt_pdf_url"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=False,
            )
    return count


async def _regen_sevas(
    *,
    tenant_id: str,
    app_key: str,
    output_dir: Path,
    limit: int,
    update_metadata: bool,
    renumber_existing: bool,
    temple_profile: dict[str, Any],
) -> int:
    sevas_col = get_collection("mandir_seva_bookings")
    docs = await (
        sevas_col.find({"tenant_id": tenant_id, "app_key": app_key})
        .sort("booking_date", 1)
        .limit(limit)
        .to_list(length=limit)
    )

    target = output_dir / "sevas"
    target.mkdir(parents=True, exist_ok=True)

    count = 0
    for doc in docs:
        row = _strip_mongo_id(doc)
        booking_id_text = str(row.get("id") or row.get("booking_id") or "").strip()
        if not booking_id_text:
            continue

        row["id"] = booking_id_text
        receipt_number = _receipt_number_for_seva(row)
        if renumber_existing and not SEVA_NUMBER_RE.match(receipt_number):
            receipt_number = await _next_receipt_number(
                tenant_id=tenant_id,
                app_key=app_key,
                receipt_kind="seva",
                receipt_date=row.get("booking_date") or row.get("seva_date") or row.get("created_at"),
            )
        row["receipt_number"] = receipt_number
        row["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id_text}/receipt/pdf"

        pdf_bytes = _generate_seva_receipt_pdf_bytes(
            row,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
        file_name = f"seva_receipt_{_safe_name(row['receipt_number'], booking_id_text[:8])}.pdf"
        (target / file_name).write_bytes(pdf_bytes)
        count += 1

        if update_metadata:
            await sevas_col.update_one(
                {"tenant_id": tenant_id, "app_key": app_key, "id": booking_id_text},
                {
                    "$set": {
                        "receipt_number": row["receipt_number"],
                        "receipt_pdf_url": row["receipt_pdf_url"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
                upsert=False,
            )
    return count


async def _run(args: argparse.Namespace) -> int:
    await init_mongo()
    try:
        temple_profile = await _resolve_temple_profile(args.tenant_id, args.app_key, args.lang)
        out_root = args.output_dir.resolve()
        out_root.mkdir(parents=True, exist_ok=True)

        donation_count = 0
        seva_count = 0
        if args.kind in {"all", "donation"}:
            donation_count = await _regen_donations(
                tenant_id=args.tenant_id,
                app_key=args.app_key,
                output_dir=out_root,
                limit=args.limit,
                update_metadata=args.update_metadata,
                renumber_existing=args.renumber_existing,
                temple_profile=temple_profile,
            )
        if args.kind in {"all", "seva"}:
            seva_count = await _regen_sevas(
                tenant_id=args.tenant_id,
                app_key=args.app_key,
                output_dir=out_root,
                limit=args.limit,
                update_metadata=args.update_metadata,
                renumber_existing=args.renumber_existing,
                temple_profile=temple_profile,
            )

        print(f"Done. Donations regenerated: {donation_count}, Sevas regenerated: {seva_count}")
        print(f"Output folder: {out_root}")
        if temple_profile.get("local_language"):
            print(f"Receipt local language used: {temple_profile.get('local_language')}")
        return 0
    finally:
        await close_mongo()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bulk regenerate MandirMitra receipt PDFs")
    parser.add_argument("--tenant-id", required=True, help="Tenant ID to process")
    parser.add_argument("--app-key", default="mandirmitra", help="App key (default: mandirmitra)")
    parser.add_argument("--kind", choices=["all", "donation", "seva"], default="all", help="Receipt type to regenerate")
    parser.add_argument("--limit", type=int, default=200, help="Max records per type (default: 200)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts") / "receipts_regenerated",
        help="Output root directory for generated PDFs",
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Optional language override (e.g. KN/TN/ML/TL/HI or kannada/tamil/malayalam/telugu/hindi)",
    )
    parser.add_argument(
        "--update-metadata",
        action="store_true",
        help="Also update receipt_number/receipt_pdf_url fields in Mongo documents",
    )
    parser.add_argument(
        "--renumber-existing",
        action="store_true",
        help="Convert legacy receipt numbers to DON-0000001/SEV-0000001 format for docs missing the new pattern",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
