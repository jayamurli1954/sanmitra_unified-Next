#!/usr/bin/env python3
"""Guarded launcher for the MandirMitra Stage 3 destructive demo E2E.

Secrets are prompted without echo and passed only to the child Playwright
process. The launcher never accepts password command-line arguments and writes
only sanitized gate metadata to its evidence file.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SPEC = "e2e/mandirmitra-donation-realstack-destructive.spec.js"
DEMO_MARKERS = ("demo", "test", "seed")


def origin(value: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("URL must include scheme and host")
    return f"{parsed.scheme}://{parsed.netloc}"


def validate_target(value: str, label: str) -> str:
    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute URL")
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError(f"{label} must use HTTPS unless it is loopback")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain embedded credentials")
    return value.rstrip("/")


def validate_inputs(args: argparse.Namespace) -> tuple[str, str, str]:
    frontend_url = validate_target(args.frontend_url, "frontend URL")
    api_base_url = validate_target(args.api_base_url, "API base URL")
    tenant_id = args.tenant_id.strip()
    if not tenant_id or not any(marker in tenant_id.lower() for marker in DEMO_MARKERS):
        raise ValueError("tenant ID must be explicit and visibly marked demo/test/seed")
    if not args.approver_email.strip() or not args.maker_email.strip():
        raise ValueError("distinct approver and maker emails are required")
    if args.approver_email.strip().lower() == args.maker_email.strip().lower():
        raise ValueError("approver and maker emails must be distinct")
    return frontend_url, api_base_url, tenant_id


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Run guarded MandirMitra Stage 3 demo mutations.")
    result.add_argument("--frontend-url", required=True)
    result.add_argument("--api-base-url", required=True)
    result.add_argument("--tenant-id", required=True)
    result.add_argument("--approver-email", required=True)
    result.add_argument("--maker-email", required=True)
    result.add_argument("--execute", action="store_true", help="Actually run the destructive demo suite.")
    result.add_argument(
        "--evidence",
        default=str(ROOT / "tmp" / "mandir-stage3-destructive-evidence.json"),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        frontend_url, api_base_url, tenant_id = validate_inputs(args)
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    api_origin = origin(api_base_url)
    confirmation = f"DESTROY_DEMO_ONLY:{tenant_id}@{api_origin}"
    evidence_path = Path(args.evidence)
    if not evidence_path.is_absolute():
        evidence_path = ROOT / evidence_path
    evidence_path = evidence_path.resolve()
    try:
        evidence_path.relative_to(ROOT)
    except ValueError:
        print("BLOCKED: evidence path must remain inside the workspace", file=sys.stderr)
        return 2
    if not args.execute:
        print("READY: static destructive-gate inputs are valid; no services were contacted and no data was changed.")
        print(f"Target API origin: {api_origin}")
        print(f"Demo tenant: {tenant_id}")
        print("Re-run with --execute only after the operator confirms this is an authorized demo tenant.")
        return 0

    typed_tenant = input(f"Type the demo tenant ID ({tenant_id}) to continue: ").strip()
    if typed_tenant != tenant_id:
        print("BLOCKED: typed tenant confirmation did not match", file=sys.stderr)
        return 2

    approver_password = getpass.getpass("Approver password: ")
    maker_password = getpass.getpass("Maker password: ")
    if not approver_password or not maker_password or approver_password == maker_password:
        print("BLOCKED: distinct non-empty credentials are required", file=sys.stderr)
        return 2

    npx = shutil.which("npx.cmd" if os.name == "nt" else "npx")
    if not npx:
        print("BLOCKED: npx is unavailable", file=sys.stderr)
        return 2

    child_env = os.environ.copy()
    child_env.update({
        "E2E_BASE_URL": frontend_url,
        "E2E_API_BASE_URL": api_base_url,
        "MANDIRMITRA_DEMO_TENANT_ID": tenant_id,
        "MANDIRMITRA_E2E_USER_EMAIL": args.approver_email.strip(),
        "MANDIRMITRA_E2E_USER_PASSWORD": approver_password,
        "MANDIRMITRA_E2E_MAKER_EMAIL": args.maker_email.strip(),
        "MANDIRMITRA_E2E_MAKER_PASSWORD": maker_password,
        "MANDIRMITRA_RUN_DESTRUCTIVE_E2E": "true",
        "MANDIRMITRA_DEMO_E2E_CONFIRM": confirmation,
    })
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    result = subprocess.run(
        [npx, "playwright", "test", SPEC, "--project=chromium", "--reporter=line"],
        cwd=FRONTEND,
        env=child_env,
        check=False,
    )
    for key in (
        "MANDIRMITRA_E2E_USER_PASSWORD",
        "MANDIRMITRA_E2E_MAKER_PASSWORD",
        "MANDIRMITRA_DEMO_E2E_CONFIRM",
    ):
        child_env.pop(key, None)
    del approver_password, maker_password
    evidence = {
        "gate": "mandirmitra_stage3_destructive_demo",
        "status": "passed" if result.returncode == 0 else "failed",
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "frontend_origin": origin(frontend_url),
        "api_origin": api_origin,
        "tenant_id": tenant_id,
        "organization_type_expected": "TEMPLE",
        "app_key": "mandirmitra",
        "distinct_actor_check": True,
        "demo_write_marker_check": True,
        "trace_and_video_disabled": True,
        "exit_code": result.returncode,
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Sanitized evidence: {evidence_path}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
