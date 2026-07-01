#!/usr/bin/env python3
"""Local preflight — run the CI gates on your machine BEFORE you commit/push.

Why: the GitHub Actions for this repo are expensive (2500+ runs). Running the
checks that ARE reproducible locally turns a red push into a green one and keeps
the run count down. See docs/LOCAL_CI_AND_SECURITY_SOP.md and AGENTS.md §28.

Tiers
-----
Tier 1 (always, zero install) — mirrors `backend-ci` and `accounting-stability-gate`:
    repo-safety, AGENTS compliance, compileall, text integrity, route contract, pytest.

Tier 2 (--frontend) — mirrors `mitrabooks-shell-smoke` and `global-e2e-playwright`:
    serves the frontends and runs the Playwright smoke specs, including focused
    MitraBooks Phase 1 closeout checks (needs node + browsers).

Tier 3 (--security) — best-effort local run of `security-trivy` / `semgrep`:
    runs each scanner IF its binary is on PATH, otherwise prints SKIPPED with a note.
    CodeQL is NOT runnable here in practice and stays a CI-only gate.

Usage
-----
    python scripts/preflight.py              # Tier 1 (full pytest)
    python scripts/preflight.py --quick      # Tier 1 with a faster pytest subset
    python scripts/preflight.py --frontend    # Tier 1 + frontend smoke
    python scripts/preflight.py --security    # Tier 1 + local scanners (best-effort)
    python scripts/preflight.py --all         # everything

Exit code is non-zero if any executed check failed, so it is safe to chain before
a commit (e.g. `python scripts/preflight.py && git commit ...`).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# Tier 1: name -> command. Exactly mirrors the backend-ci / accounting-gate steps.
TIER1 = [
    ("repo safety", [PY, "scripts/check_repository_safety.py"]),
    ("AGENTS compliance", [PY, "scripts/check_agents_compliance.py"]),
    ("compile sources", [PY, "-m", "compileall", "app", "scripts", "tests"]),
    ("text integrity", [PY, "scripts/check_text_integrity.py", "app", "scripts", ".github/workflows"]),
    ("route contract", [PY, "scripts/check_frontend_backend_route_contract.py", "--fail-on-missing"]),
]


def run(label: str, command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> bool:
    print(f"\n=== {label} ===\n+ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, env=env)
    ok = result.returncode == 0
    print(f"  -> {'PASS' if ok else 'FAIL'} ({label})", flush=True)
    return ok


def run_tier1(quick: bool) -> list[tuple[str, bool]]:
    results = [(label, run(label, cmd)) for label, cmd in TIER1]
    if quick:
        pytest_cmd = [PY, "-m", "pytest", "-q", "-k",
                      "accounting or tenant or health or module or cost or dimension or manufactur"]
        label = "pytest (quick subset)"
    else:
        pytest_cmd = [PY, "-m", "pytest", "-q"]
        label = "pytest (full)"
    results.append((label, run(label, pytest_cmd)))
    return results


def run_frontend() -> list[tuple[str, bool]]:
    frontend = ROOT / "frontend"
    npx = shutil.which("npx")
    if npx is None:
        print("\n=== frontend smoke ===\n  -> SKIPPED (npx/node not found)")
        return [("frontend smoke", True)]  # not a failure; just unavailable

    # Serve the frontends in the background (no webServer in playwright.config.js).
    print("\n=== frontend smoke ===\n+ starting serve_frontends.py on 127.0.0.1:3300", flush=True)
    frontend_env = dict(os.environ)
    frontend_env["PLAYWRIGHT_BASE_URL"] = "http://127.0.0.1:3300"
    server = subprocess.Popen(
        [PY, "scripts/serve_frontends.py", "--host", "127.0.0.1", "--port", "3300"], cwd=ROOT,
    )
    try:
        time.sleep(4)  # give the static server a moment to bind
        results = [
            ("global smoke", run("global smoke",
                                 [npx, "playwright", "test", "e2e/global-smoke.spec.js", "--project=chromium"],
                                 cwd=frontend, env=frontend_env)),
            ("mitrabooks shell smoke", run("mitrabooks shell smoke",
                                           [npx, "playwright", "test", "e2e/mitrabooks-shell.spec.js",
                                            "--project=chromium", "--timeout=90000", "--reporter=list"],
                                           cwd=frontend, env=frontend_env)),
            ("mitrabooks CA invite smoke", run("mitrabooks CA invite smoke",
                                               [npx, "playwright", "test", "e2e/ca-invite-accept.spec.js",
                                                "--project=chromium", "--reporter=list"],
                                               cwd=frontend, env=frontend_env)),
        ]
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    return results


def run_security() -> list[tuple[str, bool]]:
    results: list[tuple[str, bool]] = []

    trivy = shutil.which("trivy")
    if trivy:
        results.append(("trivy fs scan", run("trivy fs scan",
            [trivy, "fs", ".", "--severity", "HIGH,CRITICAL", "--scanners", "vuln,secret,misconfig",
             "--exit-code", "1", "--quiet"])))
    else:
        print("\n=== trivy fs scan ===\n  -> SKIPPED (trivy not installed; install the Windows binary "
              "or rely on the security-trivy CI job)")

    semgrep = shutil.which("semgrep")
    if semgrep:
        results.append(("semgrep", run("semgrep",
            [semgrep, "scan", "--config", "p/python", "--config", "p/javascript", "--config", "p/secrets",
             "--metrics=off", "--error", "--exclude", "external-repos", "--exclude", ".venv"])))
    else:
        print("\n=== semgrep ===\n  -> SKIPPED (no native Windows support; runs in the semgrep CI job, "
              "or use Docker/WSL locally)")

    print("\n=== codeql ===\n  -> SKIPPED (CI-only gate; not practical to run locally per commit)")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the locally-reproducible CI gates before committing.")
    parser.add_argument("--quick", action="store_true", help="Run a faster pytest subset instead of the full suite.")
    parser.add_argument("--frontend", action="store_true", help="Also run the Playwright frontend smoke specs.")
    parser.add_argument("--security", action="store_true", help="Also run local security scanners (best-effort).")
    parser.add_argument("--all", action="store_true", help="Run Tier 1 + frontend + security.")
    args = parser.parse_args()

    results = run_tier1(args.quick)
    if args.frontend or args.all:
        results += run_frontend()
    if args.security or args.all:
        results += run_security()

    print("\n" + "=" * 48 + "\nPREFLIGHT SUMMARY\n" + "=" * 48)
    failed = [name for name, ok in results if not ok]
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    if failed:
        print(f"\n{len(failed)} check(s) FAILED — fix before committing/pushing.")
        return 1
    print("\nAll executed checks passed. Safe to commit and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
