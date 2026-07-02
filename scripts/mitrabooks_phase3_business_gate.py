#!/usr/bin/env python3
"""Run the MitraBooks Phase 3 core business workflow signoff gate.

The gate proves the currently implemented core business workflows in two
layers:

1. backend/accounting tests for tenant-scoped parties, vouchers, invoices,
   purchase bills, credit notes, debit notes, reports, sub-ledgers, reversal,
   idempotency, and route contracts;
2. browser workflow smoke for the MitraBooks ERP shell covering create, post,
   detail, report navigation, and reversal surfaces.

Staging URLs are read-only by default. Destructive deployed browser checks are
allowed only against the documented MitraBooks business demo tenant, with an
operator confirmation and staging-only credentials supplied through the runtime
environment.
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

DESTRUCTIVE_BROWSER_SPEC = "e2e/mitrabooks-realstack-destructive.spec.js"

DEMO_TENANT_ID = "demo-mitrabooks-business"
DEMO_CONFIRM_ENV = "MITRABOOKS_DEMO_E2E_CONFIRM"
DEMO_USER_ENV = "E2E_USER_EMAIL"
DEMO_PASSWORD_ENV = "E2E_USER_PASSWORD"
DEMO_RUN_ENV = "MITRABOOKS_RUN_DESTRUCTIVE_E2E"


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


def validate_destructive_demo_policy(tenant_id: str, env: dict[str, str] | None = None) -> tuple[bool, list[str]]:
    """Fail closed unless destructive staging checks are scoped to the demo tenant."""
    runtime_env = env or os.environ
    errors: list[str] = []
    normalized_tenant = str(tenant_id or "").strip()
    confirmation = str(runtime_env.get(DEMO_CONFIRM_ENV, "")).strip()
    user_email = str(runtime_env.get(DEMO_USER_ENV, "")).strip()
    user_password = str(runtime_env.get(DEMO_PASSWORD_ENV, "")).strip()

    if normalized_tenant != DEMO_TENANT_ID:
        errors.append(f"--demo-tenant-id must be {DEMO_TENANT_ID!r}; got {normalized_tenant!r}.")
    if confirmation != DEMO_TENANT_ID:
        errors.append(f"{DEMO_CONFIRM_ENV} must equal {DEMO_TENANT_ID!r}.")
    if not user_email:
        errors.append(f"{DEMO_USER_ENV} must be set to a staging-only demo admin/operator email.")
    if not user_password:
        errors.append(f"{DEMO_PASSWORD_ENV} must be set to the staging-only demo password.")
    return (not errors, errors)


def print_destructive_demo_policy(tenant_id: str) -> bool:
    ok, errors = validate_destructive_demo_policy(tenant_id)
    print("\n=== destructive deployed demo policy ===")
    print(f"  tenant_id: {tenant_id or '<missing>'}")
    print(f"  allowed_tenant_id: {DEMO_TENANT_ID}")
    print("  allowed_app_key: mitrabooks")
    print("  allowed_organization_type: BUSINESS")
    print("  reset: reseed demo tenant before/after destructive browser mutation; never use real tenant data")
    if ok:
        print("  -> PASS (demo tenant policy and credentials are present)")
        return True
    for error in errors:
        print(f"  -> FAIL: {error}")
    return False


def run_destructive_demo_browser(staging_url: str, tenant_id: str) -> list[tuple[str, bool]]:
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== destructive deployed browser mutation ===\n  -> FAIL (npx/node not found)")
        return [("destructive deployed browser mutation", False)]

    policy_ok, errors = validate_destructive_demo_policy(tenant_id)
    if not policy_ok:
        print("\n=== destructive deployed browser mutation ===")
        for error in errors:
            print(f"  -> FAIL: {error}")
        return [("destructive deployed browser mutation policy", False)]

    env = dict(os.environ)
    env["E2E_BASE_URL"] = staging_url.rstrip("/")
    env[DEMO_RUN_ENV] = "true"
    return [
        (
            "destructive deployed browser mutation",
            run(
                "destructive deployed browser mutation",
                [npx, "playwright", "test", DESTRUCTIVE_BROWSER_SPEC, "--project=chromium", "--reporter=list"],
                cwd=FRONTEND,
                env=env,
            ),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MitraBooks Phase 3 core business workflow gate.")
    parser.add_argument("--skip-browser", action="store_true", help="Skip local Playwright browser workflow smoke.")
    parser.add_argument("--staging-url", help="Optional safe staging/demo frontend URL for read-only shell smoke.")
    parser.add_argument(
        "--destructive-demo-policy-check",
        action="store_true",
        help=(
            "Validate the opt-in safety preconditions for destructive deployed demo mutation. "
            "This does not run mutation tests."
        ),
    )
    parser.add_argument(
        "--run-destructive-demo",
        action="store_true",
        help=(
            "Run destructive deployed browser mutation against the approved demo tenant. "
            "Requires --staging-url plus the destructive demo policy env vars."
        ),
    )
    parser.add_argument("--demo-tenant-id", default=DEMO_TENANT_ID)
    args = parser.parse_args()

    if args.run_destructive_demo:
        args.destructive_demo_policy_check = True
        if not args.staging_url:
            print("--run-destructive-demo requires --staging-url.")
            return 2

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

    if args.destructive_demo_policy_check:
        results.append(
            (
                "destructive deployed demo policy",
                print_destructive_demo_policy(args.demo_tenant_id),
            )
        )
    else:
        print("\n=== destructive deployed demo policy ===")
        print("  -> SKIPPED (pass --destructive-demo-policy-check after seeding the demo tenant)")

    if args.run_destructive_demo:
        results += run_destructive_demo_browser(args.staging_url, args.demo_tenant_id)
    else:
        print("\n=== destructive deployed browser mutation ===")
        print("  -> SKIPPED (pass --run-destructive-demo after reset/reseed and policy confirmation)")

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
    if not args.destructive_demo_policy_check:
        print("Destructive deployed mutation remains opt-in and demo-tenant guarded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
