#!/usr/bin/env python3
"""Run the MitraBooks Phase 3 core business workflow signoff gate.

The gate proves the currently implemented core business workflows in two
layers:

1. backend/accounting tests for tenant-scoped parties, vouchers, invoices,
   purchase bills, credit notes, debit notes, reports, sub-ledgers, reversal,
   idempotency, and route contracts;
2. browser workflow smoke for the MitraBooks ERP shell covering create, post,
   detail, report navigation, and reversal surfaces.

Staging URLs are read-only unless a separate demo-tenant reset policy is
approved. Do not run destructive browser mutations against real tenant data.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PY = sys.executable

BACKEND_WORKFLOW_TESTS = [
    "tests/test_business_phase2.py",
    "tests/test_mitrabooks_erp_core_smoke.py",
    "tests/test_business_route_contract.py",
    "tests/test_accounting_report_drilldown.py",
    "tests/test_accounting_report_verification.py",
    "tests/test_party_subledger.py",
    "tests/test_payment_allocation.py",
    "tests/test_statements.py",
    "tests/test_report_export.py",
    "tests/test_invoice_pdf.py",
]

FRONTEND_CONTRACT_TESTS = [
    "tests/test_mitrabooks_frontend_local_api.py",
]

LOCAL_BROWSER_SPECS = [
    "e2e/mitrabooks-shell.spec.js",
]


def run(label: str, command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> bool:
    print(f"\n=== {label} ===\n+ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env)
    ok = result.returncode == 0
    print(f"  -> {'PASS' if ok else 'FAIL'} ({label})", flush=True)
    return ok


def run_pytest_group(label: str, files: list[str]) -> bool:
    return run(label, [PY, "-m", "pytest", "-q", *files])


def run_local_browser_smoke() -> list[tuple[str, bool]]:
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== local business browser smoke ===\n  -> FAIL (npx/node not found)")
        return [("local business browser smoke", False)]

    env = dict(os.environ)
    env["PLAYWRIGHT_BASE_URL"] = "http://127.0.0.1:3300"
    print("\n=== local browser server ===\n+ starting serve_frontends.py on 127.0.0.1:3300", flush=True)
    server = subprocess.Popen(
        [PY, "scripts/serve_frontends.py", "--host", "127.0.0.1", "--port", "3300"],
        cwd=ROOT,
    )
    try:
        time.sleep(4)
        return [
            (
                f"local business browser smoke: {spec}",
                run(
                    f"local business browser smoke: {spec}",
                    [npx, "playwright", "test", spec, "--project=chromium", "--reporter=list"],
                    cwd=FRONTEND,
                    env=env,
                ),
            )
            for spec in LOCAL_BROWSER_SPECS
        ]
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def run_staging_read_only_smoke(staging_url: str) -> list[tuple[str, bool]]:
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== staging browser smoke ===\n  -> FAIL (npx/node not found)")
        return [("staging browser smoke", False)]

    parsed = urlparse(staging_url)
    if not parsed.path.rstrip("/").endswith("/mitrabooks-erp"):
        print("\n=== staging smoke scope ===")
        print("  -> Staging URL is not a direct /mitrabooks-erp/ target; using MitraBooks shell smoke anyway.")

    env = dict(os.environ)
    env["E2E_BASE_URL"] = staging_url.rstrip("/")
    return [
        (
            "staging read-only MitraBooks shell smoke",
            run(
                "staging read-only MitraBooks shell smoke",
                [npx, "playwright", "test", "e2e/mitrabooks-shell.spec.js", "--project=chromium", "--reporter=list"],
                cwd=FRONTEND,
                env=env,
            ),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MitraBooks Phase 3 core business workflow gate.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip local Playwright browser workflow smoke.")
    parser.add_argument("--staging-url", help="Optional safe staging/demo frontend URL for read-only shell smoke.")
    args = parser.parse_args()

    results: list[tuple[str, bool]] = [
        ("backend business workflow pytest", run_pytest_group("backend business workflow pytest", BACKEND_WORKFLOW_TESTS)),
        ("frontend business contract pytest", run_pytest_group("frontend business contract pytest", FRONTEND_CONTRACT_TESTS)),
    ]

    if args.skip_browser:
        print("\n=== local business browser smoke ===\n  -> SKIPPED by --skip-browser")
    else:
        results += run_local_browser_smoke()

    if args.staging_url:
        results += run_staging_read_only_smoke(args.staging_url)
    else:
        print("\n=== staging business smoke ===")
        print("  -> SKIPPED (pass --staging-url for read-only deployed shell smoke)")

    print("\n" + "=" * 60)
    print("MITRABOOKS PHASE 3 BUSINESS WORKFLOW GATE SUMMARY")
    print("=" * 60)
    failed = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if failed:
        print(f"\n{len(failed)} check(s) FAILED. Phase 3 core workflow signoff is not closed.")
        return 1
    print("\nAll executed Phase 3 core business workflow checks passed.")
    if not args.staging_url:
        print("Staging shell validation remains optional/read-only unless a safe demo tenant is approved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
