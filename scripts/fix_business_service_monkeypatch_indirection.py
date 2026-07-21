"""Route patchable symbols through business_service facade at call time.

Pure-move modularization left many services binding get_collection /
post_journal_entry / etc. at import time, so tests that monkeypatch
app.modules.business.service no longer apply. Match document_attachments /
gst_period_locks: resolve via business_service.<name> at runtime.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "app" / "modules" / "business" / "services"
FACADE = ROOT / "app" / "modules" / "business" / "service.py"

# Callables tests monkeypatch on the facade (and must be looked up at runtime).
PATCHABLE = [
    "get_collection",
    "post_journal_entry",
    "reverse_journal_entry",
    "initialize_default_chart_of_accounts",
    "validate_dimension_refs",
    "_resolve_voucher_account_id",
    "is_gst_period_locked",
    "set_gst_period_lock",
    "_compensate_gst_settlement_failure",
    "_reverse_after_domain_persistence_failure",
    "_reserve_voucher_number",
    "_reserve_invoice_number",
    "_reserve_sequence_number",
    "_compute_itc_interest",
]

# Names that may stay imported from the facade (constants / non-patched helpers).
# Patchable names are stripped from `from ... service import (...)` lists.


def _ensure_business_service_import(text: str) -> str:
    if "import service as business_service" in text:
        return text
    # Prefer after sqlalchemy / accounting schema imports.
    marker = "from app.modules.business.schemas import"
    if marker in text:
        return text.replace(
            marker,
            "from app.modules.business import service as business_service\n" + marker,
            1,
        )
    marker2 = "from app.modules.business.service import"
    if marker2 in text:
        return text.replace(
            marker2,
            "from app.modules.business import service as business_service\n" + marker2,
            1,
        )
    # Fallback: after future / first imports block
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from ") or line.startswith("import "):
            insert_at = i + 1
        elif line.strip() == "" and insert_at:
            continue
        elif insert_at and not (line.startswith("from ") or line.startswith("import ")):
            break
    lines.insert(insert_at, "from app.modules.business import service as business_service\n")
    return "".join(lines)


def _remove_mongo_get_collection(text: str) -> str:
    return text.replace("from app.db.mongo import get_collection\n", "")


def _strip_accounting_callables(text: str) -> str:
    """Keep exception classes; drop patchable callables from accounting.service import."""

    def keep_from_block(block: str) -> str:
        keep = []
        for name in ("AccountingNotFoundError", "AccountingValidationError"):
            if name in block:
                keep.append(name)
        if not keep:
            return ""
        if len(keep) == 1:
            return f"from app.accounting.service import {keep[0]}\n"
        return (
            "from app.accounting.service import (\n"
            + "".join(f"    {n},\n" for n in keep)
            + ")\n"
        )

    text = re.sub(
        r"from app\.accounting\.service import \([^)]*\)\n",
        lambda m: keep_from_block(m.group(0)),
        text,
        flags=re.S,
    )
    # Single-line form: from app.accounting.service import A, B, post_journal_entry
    text = re.sub(
        r"from app\.accounting\.service import ([^\n(]+)\n",
        lambda m: keep_from_block(m.group(0)),
        text,
    )
    return text


def _remove_dimensions_import(text: str) -> str:
    return text.replace(
        "from app.modules.business.dimensions import validate_dimension_refs\n",
        "",
    )


def _strip_patchable_from_service_import(text: str) -> str:
    pattern = re.compile(
        r"from app\.modules\.business\.service import \((.*?)\)\n",
        re.S,
    )

    def repl(match: re.Match[str]) -> str:
        body = match.group(1)
        names = []
        for line in body.splitlines():
            item = line.strip().rstrip(",")
            if not item or item.startswith("#"):
                continue
            # handle "NAME," or "NAME as NAME"
            base = item.split(" as ")[0].strip()
            if base in PATCHABLE:
                continue
            names.append(item)
        if not names:
            return ""
        if len(names) == 1 and "\n" not in body.strip():
            return f"from app.modules.business.service import {names[0]}\n"
        inner = "".join(f"    {n},\n" for n in names)
        return f"from app.modules.business.service import (\n{inner})\n"

    return pattern.sub(repl, text)


# Names defined in a module must not be rewritten to business_service.X inside that module.
DEFINED_IN = {
    "common.py": {"_resolve_voucher_account_id"},
    "itc_reversal.py": {"_compute_itc_interest"},
    "gst_period_locks.py": {"is_gst_period_locked", "set_gst_period_lock"},
    "document_numbering.py": {"_reserve_sequence_number"},
    "invoice_computation.py": {"_reserve_invoice_number"},
}


def _qualify_patchable_calls(text: str, *, skip_names: set[str] | None = None) -> str:
    skip = skip_names or set()
    # Protect definitions so we do not rewrite `def name(` / `async def name(`.
    protected: list[tuple[str, str]] = []
    for name in PATCHABLE:
        for prefix in ("async def ", "def "):
            needle = f"{prefix}{name}("
            if needle in text:
                token = f"__DEF_{name}__("
                text = text.replace(needle, f"{prefix}{token}")
                protected.append((f"{prefix}{token}", needle))

    for name in PATCHABLE:
        if name in skip:
            continue
        text = re.sub(
            rf"(?<![\w.]){name}(\s*\()",
            rf"business_service.{name}\1",
            text,
        )
    # Restore protected defs
    for name in PATCHABLE:
        text = text.replace(f"async def __DEF_{name}__(", f"async def {name}(")
        text = text.replace(f"def __DEF_{name}__(", f"def {name}(")
    return text


def convert_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    text = original

    if path.name == "indexes.py":
        # Already resolves get_collection via business_service at call time.
        return False

    lagging = {
        "common.py",
        "vouchers.py",
        "sales_invoices.py",
        "purchase_bills.py",
        "credit_notes.py",
        "debit_notes.py",
        "gst_settlement.py",
        "itc_reversal.py",
        "parties.py",
        "party_ledger.py",
        "ca_clients.py",
    }
    if path.name not in lagging:
        return False

    if path.name == "common.py":
        text = _ensure_business_service_import(text)
        text = text.replace(
            "from app.accounting.service import AccountingNotFoundError, initialize_default_chart_of_accounts\n",
            "from app.accounting.service import AccountingNotFoundError\n",
        )
        text = _qualify_patchable_calls(text, skip_names=DEFINED_IN.get(path.name, set()))
        if text != original:
            path.write_text(text, encoding="utf-8", newline="\n")
            return True
        return False

    text = _ensure_business_service_import(text)
    text = _remove_mongo_get_collection(text)
    text = _strip_accounting_callables(text)
    text = _remove_dimensions_import(text)
    text = _strip_patchable_from_service_import(text)
    text = _qualify_patchable_calls(text, skip_names=DEFINED_IN.get(path.name, set()))
    text = text.replace("business_service.business_service.", "business_service.")

    if path.name == "vouchers.py":
        text = text.replace(
            "from app.modules.business.services.common import (\n"
            "    _audit_business_event,\n"
            "    _ensure_business_chart_for_voucher_codes,\n"
            "    _json_safe_doc,\n"
            "    _money,\n"
            "    _now,\n"
            "    _resolve_voucher_account_id,\n"
            "    _voucher_response_doc,\n"
            ")\n",
            "from app.modules.business.services.common import (\n"
            "    _audit_business_event,\n"
            "    _ensure_business_chart_for_voucher_codes,\n"
            "    _json_safe_doc,\n"
            "    _money,\n"
            "    _now,\n"
            "    _voucher_response_doc,\n"
            ")\n",
        )
        text = re.sub(
            r"from app\.accounting\.service import \(\n"
            r"    AccountingNotFoundError,\n"
            r"    AccountingValidationError,\n"
            r"    initialize_default_chart_of_accounts,\n"
            r"    post_journal_entry,\n"
            r"    reverse_journal_entry,\n"
            r"\)\n",
            "from app.accounting.service import (\n"
            "    AccountingNotFoundError,\n"
            "    AccountingValidationError,\n"
            ")\n",
            text,
        )

    if text != original:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def patch_facade() -> bool:
    text = FACADE.read_text(encoding="utf-8")
    original = text
    old = """from app.accounting.service import (
    AccountingValidationError,
    reverse_journal_entry,
)"""
    new = """from app.accounting.service import (
    AccountingNotFoundError as AccountingNotFoundError,
    AccountingValidationError as AccountingValidationError,
    initialize_default_chart_of_accounts as initialize_default_chart_of_accounts,
    post_journal_entry as post_journal_entry,
    reverse_journal_entry as reverse_journal_entry,
)
from app.modules.business.dimensions import validate_dimension_refs as validate_dimension_refs"""
    if old in text:
        text = text.replace(old, new, 1)
    # Re-export _compute_itc_interest from itc_reversal block
    old_itc = """from app.modules.business.services.itc_reversal import (  # noqa: E402
    mark_bill_payment as mark_bill_payment,
    preview_itc_reversals as preview_itc_reversals,
    reclaim_itc_for_bill as reclaim_itc_for_bill,
    reverse_itc_for_bill as reverse_itc_for_bill,
)"""
    new_itc = """from app.modules.business.services.itc_reversal import (  # noqa: E402
    _compute_itc_interest as _compute_itc_interest,
    mark_bill_payment as mark_bill_payment,
    preview_itc_reversals as preview_itc_reversals,
    reclaim_itc_for_bill as reclaim_itc_for_bill,
    reverse_itc_for_bill as reverse_itc_for_bill,
)"""
    if old_itc in text and "_compute_itc_interest as _compute_itc_interest" not in text:
        text = text.replace(old_itc, new_itc, 1)
    if text != original:
        FACADE.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> None:
    changed = []
    if patch_facade():
        changed.append(str(FACADE.relative_to(ROOT)))
    for path in sorted(SERVICES.glob("*.py")):
        if convert_file(path):
            changed.append(str(path.relative_to(ROOT)))
    print("Updated:")
    for c in changed:
        print(f"  {c}")
    print(f"Total: {len(changed)}")


if __name__ == "__main__":
    main()
