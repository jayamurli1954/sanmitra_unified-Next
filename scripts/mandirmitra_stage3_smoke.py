#!/usr/bin/env python3
"""Stage 3 MandirMitra live-readiness smoke runner.

This runner is intentionally non-destructive. It executes compile checks and
focused pytest suites that validate MandirMitra receipts, accounting posting,
tenant/app isolation, and shared accounting drill-down behavior.

Live browser/API data-creation checks remain in the companion operations
checklist because they depend on a running local/staging backend and operator
confirmation of generated PDFs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMPILE_TARGETS = [
    "app/accounting",
    "app/modules/mandir_compat",
    "app/core/tenants",
    "app/core/modules",
    "scripts",
]

SHARED_FOCUSED_TESTS = [
    "tests/test_accounting_report_drilldown.py",
    "tests/test_accounting_app_key_isolation.py",
    "tests/test_tenants_lifecycle.py",
    "tests/test_modules_me_endpoint.py",
    "tests/test_module_access_dependency.py",
    "tests/test_platform_owner_dashboard.py",
]


def existing(paths: list[str]) -> list[str]:
    return [path for path in paths if (ROOT / path).exists()]


def run(command: list[str]) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def print_manual_gate() -> None:
    print()
    print("Manual/live Stage 3 checks still required before live-ready signoff:")
    print("1. Login to http://127.0.0.1:3300/mitrabooks-erp/# as admin@sanmitra.local.")
    print("2. Confirm /api/v1/modules/me returns TEMPLE with temple, accounting, audit for mandirmitra.")
    print("3. Create one donation, one seva booking, and one MandirMitra expense.")
    print("4. Download/preview donation PDF and confirm title, donation terminology, and no seva-only note.")
    print("5. Download/preview seva PDF and confirm title, devotee label, and Kannada seva received sentence.")
    print("6. Confirm Trial Balance balances and rows drill down to vouchers.")
    print("7. Confirm Income & Expenditure, Receipts & Payments, and Balance Sheet match posted vouchers.")
    print("8. Verify public devotee no-login payment flow: temple/trust selection, donation/seva choice, amount, and configured UPI/payment instructions.")
    print("9. Verify exception handling: pending payment verify, reject, correction, receipt preview/download, and audit trace.")
    print("10. Verify tenant/app isolation with mandirmitra, gruhamitra, and mitrabooks app contexts.")
    print("11. Verify 80G/FCRA tenant configuration is default-off or backed by complete dated approval evidence.")
    print("12. Verify compliance donation controls fail closed and readiness reports mask PAN and remain non-filing artifacts.")
    print()
    print("Checklist source: docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MandirMitra Stage 3 smoke checks.")
    parser.add_argument("--skip-compile", action="store_true", help="Skip Python compile checks.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip focused pytest checks.")
    parser.add_argument(
        "--pytest-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Extra arguments passed to pytest after focused test paths.",
    )
    args = parser.parse_args()

    if not args.skip_compile:
        compile_targets = existing(COMPILE_TARGETS)
        if compile_targets:
            run([sys.executable, "-m", "compileall", *compile_targets])

    if not args.skip_tests:
        mandir_tests = sorted(
            str(path.relative_to(ROOT))
            for path in (ROOT / "tests").glob("test_mandir*.py")
        )
        test_paths = [*mandir_tests, *existing(SHARED_FOCUSED_TESTS)]
        if not test_paths:
            print("No focused MandirMitra Stage 3 tests found.")
            raise SystemExit(1)
        run([sys.executable, "-m", "pytest", *test_paths, "-q", *args.pytest_args])

    print_manual_gate()
    print("MandirMitra Stage 3 automated smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
