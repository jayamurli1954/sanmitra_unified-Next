"""Backfill bank-reconciliation line claims for matches saved before atomic
matching (gap #14 in docs/prd/MITRABOOKS_BANK_RECON_GAP_ANALYSIS.md).

Every live match (active or pending a difference voucher) gets a claim for
each statement line and book line it holds, so those lines are protected
against two users matching them at the same moment. Safe to re-run.

Lines held by two different live matches are reported as conflicts and left
unchanged; an accountant should unmatch one of them.

Usage:
  python scripts/backfill_bank_recon_claims.py --app-key mitrabooks --dry-run
  python scripts/backfill_bank_recon_claims.py --app-key mitrabooks [--tenant-id T]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.mongo import close_mongo, init_mongo
from app.modules.business.bank_recon import backfill_bank_recon_claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--app-key", default="mitrabooks")
    parser.add_argument("--tenant-id", default=None, help="Limit to one tenant (default: all tenants).")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing.")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    await init_mongo()
    try:
        summary = await backfill_bank_recon_claims(
            app_key=args.app_key, tenant_id=args.tenant_id, dry_run=args.dry_run,
        )
    finally:
        await close_mongo()
    print(json.dumps(summary, indent=2, default=str))
    if summary["conflicts"]:
        print(
            f"\n{len(summary['conflicts'])} line(s) are held by two live matches. "
            "Unmatch one match for each before relying on reconciliation for those accounts.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
