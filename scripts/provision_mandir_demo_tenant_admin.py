#!/usr/bin/env python3
"""Provision a Demo Temple tenant_admin on hosted Mandir staging via Super Admin API.

Read-only discovery of temple_id → tenant_id, then POST /api/v1/users
(no trailing slash: /users/ is a Mandir/Gruha GET-only compat path and returns 405).
Prompts for Super Admin password and the new admin password (never logged).
Does not touch production.
"""

from __future__ import annotations

import getpass
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"
DEFAULT_APP_KEY = "mandirmitra"
DEFAULT_SUPERADMIN_EMAIL = "superadmin@sanmitra.local"
DEFAULT_TEMPLE_ID = 1
DEFAULT_ADMIN_EMAIL = "temple.demo.admin@sanmitratech.in"
DEFAULT_ADMIN_NAME = "Demo Temple Admin"


def _request_json(request: Request, timeout: int = 30) -> tuple[int, dict | list]:
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            body = response.read().decode("utf-8")
            return status, json.loads(body or "{}")
    except HTTPError as exc:
        payload: dict | list = {"detail": exc.reason}
        try:
            payload = json.loads(exc.read().decode("utf-8") or "{}")
        except Exception:
            pass
        return int(exc.code), payload


def _detail(payload: dict | list) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        return str(payload or "unknown error")
    return str(payload)


def _post_json(url: str, headers: dict, body: dict) -> tuple[int, dict | list]:
    req = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    return _request_json(req)


def _get_json(url: str, headers: dict) -> tuple[int, dict | list]:
    req = Request(url, headers=headers, method="GET")
    return _request_json(req)


def main() -> int:
    api_base = str(os.getenv("STAGING_API_BASE_URL", DEFAULT_API_BASE)).strip().rstrip("/")
    if "onrender.com" not in api_base and "localhost" not in api_base and "127.0.0.1" not in api_base:
        print("FAIL: refusing unexpected API host. Set STAGING_API_BASE_URL to staging or loopback.")
        return 2

    app_key = str(os.getenv("STAGING_APP_KEY", DEFAULT_APP_KEY)).strip() or DEFAULT_APP_KEY
    super_email = str(os.getenv("MANDIR_SUPERADMIN_EMAIL", DEFAULT_SUPERADMIN_EMAIL)).strip()
    temple_id_raw = str(os.getenv("MANDIR_DEMO_TEMPLE_ID", str(DEFAULT_TEMPLE_ID))).strip()
    try:
        temple_id = int(temple_id_raw)
    except ValueError:
        print(f"FAIL: MANDIR_DEMO_TEMPLE_ID must be an integer, got {temple_id_raw!r}")
        return 2

    admin_email = str(os.getenv("MANDIR_DEMO_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)).strip().lower()
    admin_name = str(os.getenv("MANDIR_DEMO_ADMIN_NAME", DEFAULT_ADMIN_NAME)).strip() or DEFAULT_ADMIN_NAME
    admin_password = str(os.getenv("MANDIR_DEMO_ADMIN_PASSWORD", "")).strip()
    super_password = str(os.getenv("MANDIR_SUPERADMIN_PASSWORD", "")).strip()

    if sys.stdin.isatty():
        if not super_password:
            super_password = getpass.getpass(f"Super Admin password for {super_email}: ").strip()
        if not admin_password:
            admin_password = getpass.getpass(f"New password for {admin_email}: ").strip()
            confirm = getpass.getpass("Confirm new password: ").strip()
            if admin_password != confirm:
                print("FAIL: password confirmation did not match.")
                return 2

    if not super_password:
        print("FAIL: set MANDIR_SUPERADMIN_PASSWORD or run interactively.")
        return 2
    if len(admin_password) < 8:
        print("FAIL: new admin password must be at least 8 characters.")
        return 2
    if not admin_email or "@" not in admin_email:
        print("FAIL: set MANDIR_DEMO_ADMIN_EMAIL to a valid email.")
        return 2
    if admin_email.endswith(".local") or admin_email.endswith(".localhost"):
        print(
            "FAIL: staging rejects reserved domains like .local on user create (HTTP 422). "
            "Use e.g. temple.demo.admin@sanmitratech.in"
        )
        return 2
    if admin_email == super_email.lower():
        print("FAIL: Demo Temple admin email must differ from Super Admin.")
        return 2

    login_status, login_payload = _post_json(
        f"{api_base}/api/v1/auth/login",
        {"X-App-Key": app_key},
        {"email": super_email, "password": super_password},
    )
    if login_status < 200 or login_status >= 300 or not isinstance(login_payload, dict):
        print(f"FAIL: Super Admin login HTTP {login_status}: {_detail(login_payload)}")
        return 1

    token = str(login_payload.get("access_token") or "").strip()
    if not token:
        print("FAIL: Super Admin login returned no access_token.")
        return 1

    auth = {
        "Authorization": f"Bearer {token}",
        "X-App-Key": app_key,
        "Content-Type": "application/json",
    }

    temples_status, temples_payload = _get_json(f"{api_base}/api/v1/temples/", auth)
    if temples_status < 200 or temples_status >= 300 or not isinstance(temples_payload, list):
        print(f"FAIL: list temples HTTP {temples_status}: {_detail(temples_payload)}")
        return 1

    match = None
    for row in temples_payload:
        if not isinstance(row, dict):
            continue
        row_id = row.get("temple_id") if row.get("temple_id") is not None else row.get("id")
        try:
            if int(row_id) == temple_id:
                match = row
                break
        except (TypeError, ValueError):
            continue

    if not match:
        print(f"FAIL: no temple with temple_id={temple_id} in Super Admin temples list.")
        print("Available Demo Editable temples:")
        for row in temples_payload:
            if isinstance(row, dict) and row.get("platform_can_write"):
                rid = row.get("temple_id") or row.get("id")
                print(f"  - id={rid} name={row.get('name') or row.get('temple_name')} tenant={row.get('tenant_id')}")
        return 1

    tenant_id = str(match.get("tenant_id") or "").strip()
    temple_name = str(match.get("name") or match.get("temple_name") or "").strip()
    can_write = bool(match.get("platform_can_write"))

    print(f"Resolved Demo Temple: id={temple_id} name={temple_name!r} tenant_id={tenant_id}")
    if not tenant_id:
        print("FAIL: temple row has empty tenant_id.")
        return 1
    if not any(marker in tenant_id.lower() for marker in ("demo", "test", "seed")):
        print(
            f"FAIL: tenant_id {tenant_id!r} is not demo/test/seed marked — refusing to create admin."
        )
        return 1
    if not can_write:
        print(
            "FAIL: platform_can_write is false on this temple. Pick a Demo Editable temple "
            "or ask Ops to mark platform_demo_temple before creating E2E actors."
        )
        return 1

    # Core users router is POST /api/v1/users (no trailing slash).
    # POST /api/v1/users/ hits compat GET-only routes → HTTP 405.
    create_status, create_payload = _post_json(
        f"{api_base}/api/v1/users",
        auth,
        {
            "email": admin_email,
            "password": admin_password,
            "full_name": admin_name,
            "tenant_id": tenant_id,
            "role": "tenant_admin",
        },
    )
    if create_status == 409:
        print(f"NOTE: user already exists: {admin_email}")
        print("      Re-run verify with that email, or choose a different MANDIR_DEMO_ADMIN_EMAIL.")
    elif create_status < 200 or create_status >= 300:
        print(f"FAIL: create user HTTP {create_status}: {_detail(create_payload)}")
        return 1
    else:
        print(f"Created tenant_admin: {admin_email} on tenant {tenant_id}")

    verify_status, verify_login = _post_json(
        f"{api_base}/api/v1/auth/login",
        {"X-App-Key": app_key},
        {"email": admin_email, "password": admin_password},
    )
    if verify_status < 200 or verify_status >= 300 or not isinstance(verify_login, dict):
        print(f"FAIL: new admin login verify HTTP {verify_status}: {_detail(verify_login)}")
        if create_status == 409:
            print("Hint: existing user password may differ from what you entered.")
        return 1

    admin_token = str(verify_login.get("access_token") or "").strip()
    admin_auth = {
        "Authorization": f"Bearer {admin_token}",
        "X-App-Key": app_key,
        "Content-Type": "application/json",
    }
    modules_status, modules_payload = _get_json(f"{api_base}/api/v1/modules/me", admin_auth)
    temple_status, temple_payload = _get_json(f"{api_base}/api/v1/temples/current", admin_auth)

    if modules_status < 200 or modules_status >= 300 or not isinstance(modules_payload, dict):
        print(f"FAIL: modules/me for new admin HTTP {modules_status}: {_detail(modules_payload)}")
        return 1
    if temple_status < 200 or temple_status >= 300 or not isinstance(temple_payload, dict):
        print(f"FAIL: temples/current for new admin HTTP {temple_status}: {_detail(temple_payload)}")
        return 1

    actual_tenant = str(modules_payload.get("tenant_id") or "").strip()
    platform_can_write = bool(temple_payload.get("platform_can_write"))
    is_placeholder = bool(temple_payload.get("is_placeholder"))

    print("PASS: Demo Temple tenant_admin is usable for Stage 3 precheck.")
    print(f" - login_email: {admin_email}")
    print(f" - tenant_id: {actual_tenant}  <-- use for --tenant-id / DESTROY_DEMO_ONLY")
    print(f" - temple_id: {temple_payload.get('temple_id') or temple_payload.get('id')}")
    print(f" - temple_name: {temple_payload.get('name') or temple_payload.get('temple_name')}")
    print(f" - platform_can_write: {platform_can_write}")
    print(f" - is_placeholder: {is_placeholder}")
    if actual_tenant != tenant_id:
        print(f"WARN: modules tenant {actual_tenant!r} != temple tenant {tenant_id!r}")
    if is_placeholder or not platform_can_write:
        print("WARN: write flag still false for this login — fix temple row before destructive E2E.")
        return 1

    print("Next: set E2E_USER_EMAIL to this admin and run scripts/verify_mandir_staging_auth.py")
    print("Destructive also needs a second distinct maker tenant_admin on the same tenant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
