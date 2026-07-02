#!/usr/bin/env python3
"""Run the focused MitraBooks Phase 2E validation gate.

This gate is intentionally narrower than full preflight. It proves the Phase 2E
risks that block production-readiness claims: accounting guardrails,
tenant/app isolation, browser smoke depth, and optional read-only staging
reachability.
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

ACCOUNTING_GUARDRAIL_TESTS = [
    "tests/test_accounting_validation.py",
    "tests/test_accounting_journal_service.py",
    "tests/test_accounting_immutability.py",
    "tests/test_accounting_reversal.py",
    "tests/test_mitrabooks_compat_posting_guardrails.py",
    "tests/test_mitrabooks_erp_core_smoke.py",
]

TENANT_APP_ISOLATION_TESTS = [
    "tests/test_accounting_app_key_isolation.py",
    "tests/test_accounting_context_isolation.py",
    "tests/test_accounting_account_route_context.py",
    "tests/test_accounting_journal_route_context.py",
    "tests/test_accounting_report_route_context.py",
    "tests/test_app_tenant_resolvers.py",
    "tests/test_module_access_dependency.py",
    "tests/test_modules_me_endpoint.py",
    "tests/test_mitrabooks_erp_core_smoke.py",
]

FRONTEND_SPECS = [
    "e2e/global-smoke.spec.js",
    "e2e/mitrabooks-shell.spec.js",
    "e2e/ca-invite-accept.spec.js",
]


def run(label: str, command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> bool:
    print(f"\n=== {label} ===\n+ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env)
    ok = result.returncode == 0
    print(f"  -> {'PASS' if ok else 'FAIL'} ({label})", flush=True)
    return ok


def run_pytest_group(label: str, test_files: list[str]) -> bool:
    return run(label, [PY, "-m", "pytest", "-q", *test_files])


def run_local_browser_smoke() -> list[tuple[str, bool]]:
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== local browser smoke ===\n  -> FAIL (npx/node not found)")
        return [("local browser smoke", False)]

    env = dict(os.environ)
    env["PLAYWRIGHT_BASE_URL"] = "http://127.0.0.1:3300"
    print("\n=== local browser server ===\n+ starting serve_frontends.py on 127.0.0.1:3300", flush=True)
    server = subprocess.Popen(
        [PY, "scripts/serve_frontends.py", "--host", "127.0.0.1", "--port", "3300"],
        cwd=ROOT,
    )
    try:
        time.sleep(4)
        results = []
        for spec in FRONTEND_SPECS:
            results.append((
                f"local browser smoke: {spec}",
                run(
                    f"local browser smoke: {spec}",
                    [npx, "playwright", "test", spec, "--project=chromium", "--reporter=list"],
                    cwd=FRONTEND,
                    env=env,
                ),
            ))
        return results
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def run_staging_smoke(staging_url: str) -> list[tuple[str, bool]]:
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== staging browser smoke ===\n  -> FAIL (npx/node not found)")
        return [("staging browser smoke", False)]

    env = dict(os.environ)
    env["E2E_BASE_URL"] = staging_url.rstrip("/")
    results = []
    parsed = urlparse(staging_url)
    if parsed.path.rstrip("/").endswith("/mitrabooks-erp"):
        specs = ("e2e/mitrabooks-shell.spec.js",)
        print("\n=== staging smoke scope ===")
        print("  -> Direct MitraBooks ERP URL detected; skipping local launcher/global smoke.")
    else:
        specs = ("e2e/global-smoke.spec.js", "e2e/mitrabooks-shell.spec.js")

    for spec in specs:
        results.append((
            f"staging read-only smoke: {spec}",
            run(
                f"staging read-only smoke: {spec}",
                [npx, "playwright", "test", spec, "--project=chromium", "--reporter=list"],
                cwd=FRONTEND,
                env=env,
            ),
        ))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MitraBooks Phase 2E focused validation gate.")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip local Playwright smoke checks.")
    parser.add_argument(
        "--staging-url",
        help="Optional safe staging/demo frontend URL for read-only browser smoke.",
    )
    args = parser.parse_args()

    results: list[tuple[str, bool]] = [
        ("accounting guardrail pytest", run_pytest_group("accounting guardrail pytest", ACCOUNTING_GUARDRAIL_TESTS)),
        ("tenant/app isolation pytest", run_pytest_group("tenant/app isolation pytest", TENANT_APP_ISOLATION_TESTS)),
    ]

    if args.skip_frontend:
        print("\n=== local browser smoke ===\n  -> SKIPPED by --skip-frontend")
    else:
        results += run_local_browser_smoke()

    if args.staging_url:
        results += run_staging_smoke(args.staging_url)
    else:
        print("\n=== staging/deployment smoke ===")
        print("  -> SKIPPED (pass --staging-url with a safe staging/demo URL for read-only browser smoke)")

    print("\n" + "=" * 56)
    print("MITRABOOKS PHASE 2E GATE SUMMARY")
    print("=" * 56)
    failed = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if failed:
        print(f"\n{len(failed)} check(s) FAILED. Phase 2E is not closed.")
        return 1
    print("\nAll executed Phase 2E checks passed.")
    if not args.staging_url:
        print("Staging/deployment validation remains a manual or opt-in URL gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
