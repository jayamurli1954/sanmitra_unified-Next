#!/usr/bin/env python3
"""Read-only MandirMitra staging auth precheck for Track 0 Mandir demo tenant."""

from __future__ import annotations

import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"
DEFAULT_APP_KEY = "mandirmitra"
DEFAULT_TENANT_ID = "demo-mandir-tenant"
DEFAULT_EMAIL = "demo.admin@sanmitra.local"
REQUIRED_MODULES = {"temple", "accounting", "audit"}


def _request_json(request: Request, timeout: int = 20) -> tuple[int, dict]:
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            body = response.read().decode("utf-8")
            return status, json.loads(body or "{}")
    except HTTPError as exc:
        payload = {"detail": exc.reason}
        try:
            payload = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            pass
        return int(exc.code), payload


def _detail(payload: dict) -> str:
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    return str(payload or "unknown error")


def main() -> int:
    api_base = str(os.getenv("STAGING_API_BASE_URL", DEFAULT_API_BASE)).strip().rstrip("/")
    app_key = str(os.getenv("STAGING_APP_KEY", DEFAULT_APP_KEY)).strip() or DEFAULT_APP_KEY
    expected_tenant = str(os.getenv("EXPECTED_TENANT_ID", DEFAULT_TENANT_ID)).strip() or DEFAULT_TENANT_ID
    email = str(os.getenv("E2E_USER_EMAIL", "")).strip()
    password = str(os.getenv("E2E_USER_PASSWORD", "")).strip()

    if sys.stdin.isatty():
        if not email:
            entered_email = input(f"Mandir staging email [{DEFAULT_EMAIL}]: ").strip()
            email = entered_email or DEFAULT_EMAIL
        if not password:
            password = getpass.getpass("Mandir staging password: ").strip()

    if not email or not password:
        print(
            "FAIL: email/password required. Run interactively or set "
            "E2E_USER_EMAIL and E2E_USER_PASSWORD in the shell."
        )
        return 2

    login_body = json.dumps({"email": email, "password": password}).encode("utf-8")
    login_req = Request(
        f"{api_base}/api/v1/auth/login",
        data=login_body,
        headers={"Content-Type": "application/json", "X-App-Key": app_key},
        method="POST",
    )

    try:
        login_status, login_payload = _request_json(login_req)
    except (OSError, URLError) as exc:
        print(f"FAIL: login request failed to reach {api_base}: {exc}")
        return 1

    if login_status < 200 or login_status >= 300:
        print(f"FAIL: login precheck returned HTTP {login_status}: {_detail(login_payload)}")
        return 1

    access_token = str(login_payload.get("access_token") or "").strip()
    if not access_token:
        print("FAIL: login precheck did not return an access token.")
        return 1

    auth_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-App-Key": app_key,
    }

    modules_req = Request(f"{api_base}/api/v1/modules/me", headers=auth_headers, method="GET")
    temple_req = Request(f"{api_base}/api/v1/temples/current", headers=auth_headers, method="GET")

    try:
        modules_status, modules_payload = _request_json(modules_req)
        temple_status, temple_payload = _request_json(temple_req)
    except (OSError, URLError) as exc:
        print(f"FAIL: context precheck failed to reach staging API: {exc}")
        return 1

    if modules_status < 200 or modules_status >= 300:
        print(f"FAIL: modules precheck returned HTTP {modules_status}: {_detail(modules_payload)}")
        return 1
    if temple_status < 200 or temple_status >= 300:
        print(f"FAIL: temples/current returned HTTP {temple_status}: {_detail(temple_payload)}")
        return 1

    actual_tenant = str(modules_payload.get("tenant_id") or "").strip()
    organization_type = str(modules_payload.get("organization_type") or "").strip().upper()
    module_keys = {
        str(item.get("module_key") or "").strip()
        for item in (modules_payload.get("enabled_modules") or [])
        if isinstance(item, dict)
    }
    missing = sorted(REQUIRED_MODULES - module_keys)
    platform_can_write = bool(temple_payload.get("platform_can_write"))
    temple_name = str(temple_payload.get("name") or temple_payload.get("temple_name") or "").strip()
    temple_numeric_id = temple_payload.get("temple_id") or temple_payload.get("id")
    is_placeholder = bool(temple_payload.get("is_placeholder"))

    def _print_context(prefix: str) -> None:
        print(f"{prefix} context:")
        print(f" - api_base: {api_base}")
        print(f" - login_email: {email}")
        print(f" - tenant_id: {actual_tenant or '(missing)'}")
        print(f" - temple_id: {temple_numeric_id if temple_numeric_id is not None else '(missing)'}")
        print(f" - temple_name: {temple_name or '(unnamed)'}")
        print(f" - organization_type: {organization_type or '(missing)'}")
        print(f" - platform_can_write: {platform_can_write}")
        print(f" - is_placeholder: {is_placeholder}")
        print(f" - modules: {', '.join(sorted(module_keys)) or '(none)'}")

    errors: list[str] = []
    if actual_tenant != expected_tenant:
        # Allow default expected id; operator should copy the printed tenant_id for destructive runs.
        if expected_tenant != DEFAULT_TENANT_ID:
            errors.append(f"tenant mismatch: expected {expected_tenant!r}, got {actual_tenant!r}")
    if not any(marker in actual_tenant.lower() for marker in ("demo", "test", "seed")):
        errors.append(
            f"tenant_id {actual_tenant!r} is not marked demo/test/seed (destructive gate will refuse it)"
        )
    if organization_type != "TEMPLE":
        errors.append(f"organization_type mismatch: expected 'TEMPLE', got {organization_type!r}")
    if missing:
        errors.append(f"missing required modules: {', '.join(missing)}")
    if is_placeholder:
        errors.append(
            "temples/current returned a placeholder (no mandir_temples row for this tenant+app_key)"
        )
    if not platform_can_write:
        errors.append("platform_can_write is not true (Demo Editable required for destructive E2E)")

    if errors:
        print("FAIL: Mandir staging auth/context check failed.")
        for err in errors:
            print(f" - {err}")
        _print_context("Resolved")
        if not platform_can_write:
            print("Hint: Platform Owners 'Demo Editable' is based on the temples list.")
            print("      /temples/current uses the logged-in user's tenant_id + X-App-Key.")
            print("      If this login is Parlathaya/real, or the temple row lacks platform_can_write,")
            print("      or the row has a different/missing app_key, this check fails.")
            print("Fix options (Ops, staging only):")
            print("  1) Login as the Demo Temple admin shown under that Demo Editable row.")
            print("  2) Or mark/recreate that temple with platform_demo_temple=true (platform onboard).")
            print("  3) Or staging-only DEMO_MANDIR_BOOTSTRAP=true redeploy for demo-mandir-tenant.")
        return 1

    print("PASS: Mandir staging demo tenant context verified.")
    _print_context("Verified")
    print(f" - tenant_id for destructive --tenant-id: {actual_tenant}")
    print(f" - required modules present: {', '.join(sorted(REQUIRED_MODULES))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
