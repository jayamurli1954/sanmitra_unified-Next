#!/usr/bin/env python3
"""Read-only staging auth precheck for Track 0 credentials ops."""

from __future__ import annotations

import json
import getpass
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"
DEFAULT_APP_KEY = "mitrabooks"
DEFAULT_TENANT_ID = "demo-mitrabooks-business"
DEFAULT_EMAIL = "business.admin@sanmitra.local"
REQUIRED_MODULES = {"business", "accounting", "audit"}


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
      entered_email = input(f"Staging email [{DEFAULT_EMAIL}]: ").strip()
      email = entered_email or DEFAULT_EMAIL
    if not password:
      password = getpass.getpass("Staging password: ").strip()

  if not email or not password:
    print(
      "FAIL: staging email/password are required. Run interactively for secure prompts "
      "or set E2E_USER_EMAIL and E2E_USER_PASSWORD in the current process."
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

  modules_req = Request(
    f"{api_base}/api/v1/modules/me",
    headers={
      "Authorization": f"Bearer {access_token}",
      "Content-Type": "application/json",
      "X-App-Key": app_key,
    },
    method="GET",
  )

  try:
    modules_status, modules_payload = _request_json(modules_req)
  except (OSError, URLError) as exc:
    print(f"FAIL: modules precheck failed to reach {api_base}/api/v1/modules/me: {exc}")
    return 1

  if modules_status < 200 or modules_status >= 300:
    print(f"FAIL: modules precheck returned HTTP {modules_status}: {_detail(modules_payload)}")
    return 1

  actual_tenant = str(modules_payload.get("tenant_id") or "").strip()
  organization_type = str(modules_payload.get("organization_type") or "").strip().upper()
  module_keys = {
    str(item.get("module_key") or "").strip()
    for item in (modules_payload.get("enabled_modules") or [])
    if isinstance(item, dict)
  }
  missing = sorted(REQUIRED_MODULES - module_keys)

  errors: list[str] = []
  if actual_tenant != expected_tenant:
    errors.append(f"tenant mismatch: expected {expected_tenant!r}, got {actual_tenant!r}")
  if organization_type != "BUSINESS":
    errors.append(f"organization_type mismatch: expected 'BUSINESS', got {organization_type!r}")
  if missing:
    errors.append(f"missing required modules: {', '.join(missing)}")

  if errors:
    print("FAIL: staging auth context check failed.")
    for err in errors:
      print(f" - {err}")
    return 1

  print("PASS: staging auth credentials and tenant context verified.")
  print(f" - api_base: {api_base}")
  print(f" - tenant_id: {actual_tenant}")
  print(f" - organization_type: {organization_type}")
  print(f" - required modules present: {', '.join(sorted(REQUIRED_MODULES))}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
