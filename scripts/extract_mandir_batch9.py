"""Mechanical extraction for mandir_compat batch 9 (account resolvers).

Pure move-and-re-import only:
- Moves async account resolver helpers from app/modules/mandir_compat/router.py
  into app/modules/mandir_compat/helpers/account_resolvers.py.
- Does NOT touch quarantined receipt sequencing/cancellation or panchang code.

Run: python scripts/extract_mandir_batch9.py
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/modules/mandir_compat/router.py"


def read_lines() -> list[str]:
    return ROUTER.read_text(encoding="utf-8").splitlines(keepends=True)


def find_index(lines: list[str], predicate) -> int:
    for i, l in enumerate(lines):
        if predicate(l):
            return i
    raise RuntimeError("Anchor not found")


def main() -> None:
    lines = read_lines()

    start = find_index(
        lines,
        lambda l: l.strip().startswith("async def _normalize_mandir_income_accounts"),
    )
    end = find_index(
        lines,
        lambda l: l.strip().startswith("def _mandir_actor_id"),
    )

    # Keep everything around the section, but remove only the resolver defs block.
    del lines[start:end]

    # Insert re-export imports into the existing "Shared helpers moved..." footer block.
    insert_anchor = find_index(
        lines,
        lambda l: l.strip().startswith("from app.modules.mandir_compat.helpers.tenant_platform import"),
    )
    # Find the end of tenant_platform import block: the first line after anchor that is just ')'
    j = insert_anchor
    while j < len(lines) and lines[j].strip() != ")":
        j += 1
    if j >= len(lines):
        raise RuntimeError("tenant_platform import block end not found")

    insertion = [
        "\n",
        "# Account resolver helpers moved to helpers/account_resolvers.py; re-exported for tests.\n",
        "from app.modules.mandir_compat.helpers.account_resolvers import (\n",
        "    _normalize_mandir_income_accounts as _normalize_mandir_income_accounts,\n",
        "    _resolve_mandir_income_account as _resolve_mandir_income_account,\n",
        "    _resolve_or_create_mandir_account as _resolve_or_create_mandir_account,\n",
        "    _mandir_inventory_accounting_enabled as _mandir_inventory_accounting_enabled,\n",
        "    _resolve_mandir_in_kind_debit_account as _resolve_mandir_in_kind_debit_account,\n",
        "    _resolve_mandir_payment_account_id as _resolve_mandir_payment_account_id,\n",
        ")\n",
    ]
    # Insert right after tenant_platform block closing ')'
    lines[j + 1 : j + 1] = insertion

    ROUTER.write_text("".join(lines), encoding="utf-8")
    print("router.py updated (batch 9 extraction)")


if __name__ == "__main__":
    main()

