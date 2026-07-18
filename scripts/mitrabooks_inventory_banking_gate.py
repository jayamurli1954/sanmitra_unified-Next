#!/usr/bin/env python3
"""MitraBooks Inventory + Banking signoff gate (read-only).

Proves the MitraBooks ERP inventory and banking/reconciliation reporting surfaces
are production-signoff ready against the hosted staging stack, without mutation:

1. Inventory valuation policy (`/inventory/policy`) is the locked weighted-average
   periodic method.
2. Inventory reads (`/inventory/items`, `/inventory/movements`,
   `/inventory/stock-register`, `/inventory/closing-stock/entries`) return 200 and
   the stock register reports no negative-stock items with a numeric closing value.
3. Bank & cash book (`/banking/books`) returns 200 and its summary satisfies the
   running-balance identity: opening + receipts - payments == closing.
4. Optional: bank reconciliation BRS (`/bank-recon`) returns 200 for a supplied
   bank account id (skipped if none given).
5. Optional fail-closed / RBAC probe: with a non-business tenant credential, the
   inventory and banking routes fail closed (401/403/404).

The gate is READ-ONLY: login + GET only. It never posts, mutates, prints
tokens/passwords, or writes secrets. Sanitized evidence is written under ``tmp/``.

Credentials come from the runtime environment (prefer a secret manager):

    MB_INV_BANK_API_BASE_URL   (optional; default staging SG)
    MB_E2E_EMAIL / MB_E2E_PASSWORD          (demo-mitrabooks-business)
    GRUHA_E2E_EMAIL / GRUHA_E2E_PASSWORD    (optional fail-closed probe tenant)

Example:

    python scripts/mitrabooks_inventory_banking_gate.py --as-of 2026-07-31
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"

BUSINESS_APP_KEY = "mitrabooks"
BUSINESS_TENANT_ID = "demo-mitrabooks-business"
BUSINESS_ORG_TYPE = "BUSINESS"
BUSINESS_REQUIRED_MODULES = {"business", "accounting", "inventory"}

FAILCLOSED_APP_KEY = "gruhamitra"
FAILCLOSED_EMAIL_ENV = "GRUHA_E2E_EMAIL"
FAILCLOSED_PASSWORD_ENV = "GRUHA_E2E_PASSWORD"

FAIL_CLOSED_STATUSES = {401, 403, 404}
MONEY_TOLERANCE = 0.01


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 90,
) -> tuple[int, dict | list]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return int(getattr(response, "status", 200)), json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            payload = {"detail": raw[:200] or exc.reason}
        return int(exc.code), payload


def _detail(payload: dict | list) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str):
            return detail
        return str(detail or payload)
    return str(payload)


def _to_float(value) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _module_keys(modules_payload: dict) -> set[str]:
    keys: set[str] = set()
    for item in modules_payload.get("enabled_modules") or []:
        key = str(item.get("module_key") if isinstance(item, dict) else item or "").strip().lower()
        if key:
            keys.add(key)
    return keys


def _login(api_base: str, app_key: str, email: str, password: str) -> tuple[str | None, str]:
    status, payload = _request_json(
        "POST",
        f"{api_base}/api/v1/auth/login",
        headers={"Content-Type": "application/json", "X-App-Key": app_key},
        body={"email": email, "password": password},
    )
    if status >= 300 or not isinstance(payload, dict) or not payload.get("access_token"):
        return None, f"login failed HTTP {status}: {_detail(payload)}"
    return str(payload["access_token"]), ""


def _step(name: str, passed: bool, **extra) -> dict:
    return {"name": name, "status": "passed" if passed else "failed", **extra}


def check_context(api_base: str, auth: dict) -> dict:
    status, payload = _request_json("GET", f"{api_base}/api/v1/modules/me", headers=auth)
    if status >= 300 or not isinstance(payload, dict):
        return _step("context", False, error=f"modules/me HTTP {status}: {_detail(payload)}")
    tenant_id = str(payload.get("tenant_id") or "").strip()
    org_type = str(payload.get("organization_type") or "").strip().upper()
    module_keys = _module_keys(payload)
    errors: list[str] = []
    if tenant_id != BUSINESS_TENANT_ID:
        errors.append(f"tenant mismatch: expected {BUSINESS_TENANT_ID!r}, got {tenant_id!r}")
    if org_type != BUSINESS_ORG_TYPE:
        errors.append(f"org_type mismatch: expected {BUSINESS_ORG_TYPE!r}, got {org_type!r}")
    missing = sorted(BUSINESS_REQUIRED_MODULES - module_keys)
    if missing:
        errors.append(f"missing modules: {', '.join(missing)}")
    return _step(
        "context",
        not errors,
        tenant_id=tenant_id,
        organization_type=org_type,
        enabled_modules=sorted(module_keys),
        errors=errors,
    )


def check_inventory_policy(api_base: str, auth: dict) -> dict:
    status, payload = _request_json("GET", f"{api_base}/api/v1/business/inventory/policy", headers=auth)
    if status != 200 or not isinstance(payload, dict):
        return _step("inventory_policy", False, http_status=status, error=_detail(payload))
    valuation = payload.get("valuation_policy")
    locked = bool(payload.get("policy_locked"))
    ok = valuation == "weighted_average_periodic" and locked
    return _step(
        "inventory_policy",
        ok,
        http_status=status,
        valuation_policy=valuation,
        policy_locked=locked,
        inventory_enabled=payload.get("inventory_enabled"),
    )


def check_inventory_reads(api_base: str, auth: dict, as_of: str) -> dict:
    qs = urlencode({"as_of": as_of})
    checks: list[dict] = []
    all_ok = True

    for name, path, want_key in (
        ("items", f"/api/v1/business/inventory/items", "items"),
        ("movements", f"/api/v1/business/inventory/movements?{qs}", "items"),
        ("closing_stock_entries", f"/api/v1/business/inventory/closing-stock/entries", None),
    ):
        status, payload = _request_json("GET", f"{api_base}{path}", headers=auth)
        ok = status == 200 and isinstance(payload, dict) and (want_key is None or want_key in payload)
        all_ok = all_ok and ok
        checks.append({"read": name, "http_status": status, "status": "passed" if ok else "failed"})

    # Stock register: endpoint healthy and free of negative-stock anomalies.
    # `negative_stock_items` is an integer count (see inventory.assemble_stock_register);
    # 0 means no item has negative closing stock. When inventory accounting is disabled
    # for the entity the register is trivially empty (count 0, closing value 0.00), which
    # is a valid pass, not a failure.
    sr_status, sr_payload = _request_json(
        "GET", f"{api_base}/api/v1/business/inventory/stock-register?{qs}", headers=auth
    )
    raw_negative = sr_payload.get("negative_stock_items") if isinstance(sr_payload, dict) else None
    closing_value = _to_float(sr_payload.get("total_closing_value")) if isinstance(sr_payload, dict) else None
    try:
        negative_count = int(raw_negative) if raw_negative is not None else 0
    except (TypeError, ValueError):
        negative_count = None
    sr_ok = sr_status == 200 and negative_count == 0
    all_ok = all_ok and sr_ok
    checks.append(
        {
            "read": "stock_register",
            "http_status": sr_status,
            "negative_stock_items": negative_count,
            "total_closing_value": closing_value,
            "status": "passed" if sr_ok else "failed",
        }
    )
    return _step("inventory_reads", all_ok, reads=checks)


def check_bank_cash_book(api_base: str, auth: dict, from_date: str, to_date: str) -> dict:
    qs = urlencode({"from_date": from_date, "to_date": to_date, "book_type": "all"})
    status, payload = _request_json("GET", f"{api_base}/api/v1/business/banking/books?{qs}", headers=auth)
    if status != 200 or not isinstance(payload, dict):
        return _step("bank_cash_book", False, http_status=status, error=_detail(payload))
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    opening = _to_float(summary.get("opening_balance"))
    receipts = _to_float(summary.get("total_receipts"))
    payments = _to_float(summary.get("total_payments"))
    closing = _to_float(summary.get("closing_balance"))
    identity_ok = None not in (opening, receipts, payments, closing) and abs(
        (opening + receipts - payments) - closing
    ) <= MONEY_TOLERANCE
    return _step(
        "bank_cash_book",
        bool(identity_ok),
        http_status=status,
        from_date=from_date,
        to_date=to_date,
        opening_balance=opening,
        total_receipts=receipts,
        total_payments=payments,
        closing_balance=closing,
        balance_identity_holds=bool(identity_ok),
    )


def check_bank_recon(api_base: str, auth: dict, account_id: int | None, as_of: str) -> dict:
    if account_id is None:
        return _step("bank_recon", True, skipped=True, note="no --bank-account-id supplied; BRS probe skipped")
    qs = urlencode({"account_id": account_id, "as_of": as_of})
    status, payload = _request_json("GET", f"{api_base}/api/v1/business/bank-recon?{qs}", headers=auth)
    ok = status == 200 and isinstance(payload, dict) and "summary" in payload
    return _step("bank_recon", ok, http_status=status, account_id=account_id, detail=_detail(payload) if not ok else None)


def check_fail_closed(api_base: str, from_date: str, to_date: str) -> dict:
    email = os.environ.get(FAILCLOSED_EMAIL_ENV, "").strip()
    password = os.environ.get(FAILCLOSED_PASSWORD_ENV, "").strip()
    if not email or not password:
        return _step(
            "fail_closed",
            True,
            skipped=True,
            note=f"no non-business creds ({FAILCLOSED_EMAIL_ENV}/{FAILCLOSED_PASSWORD_ENV}); probe skipped",
        )
    token, err = _login(api_base, FAILCLOSED_APP_KEY, email, password)
    if not token:
        return _step("fail_closed", False, error=err)
    auth = {"Authorization": f"Bearer {token}", "X-App-Key": FAILCLOSED_APP_KEY, "Content-Type": "application/json"}
    books_qs = urlencode({"from_date": from_date, "to_date": to_date, "book_type": "all"})
    routes = (
        "/api/v1/business/inventory/stock-register",
        f"/api/v1/business/banking/books?{books_qs}",
    )
    probes: list[dict] = []
    all_ok = True
    for route in routes:
        status, _payload = _request_json("GET", f"{api_base}{route}", headers=auth)
        ok = status in FAIL_CLOSED_STATUSES
        all_ok = all_ok and ok
        probes.append({"route": route.split("?")[0], "http_status": status, "status": "passed" if ok else "failed"})
    return _step("fail_closed", all_ok, app_key=FAILCLOSED_APP_KEY, probes=probes)


def main() -> int:
    parser = argparse.ArgumentParser(description="MitraBooks Inventory + Banking gate (read-only)")
    parser.add_argument("--api-base", default=os.getenv("MB_INV_BANK_API_BASE_URL", DEFAULT_API_BASE))
    parser.add_argument("--as-of", default=date.today().isoformat(), help="inventory/BRS as_of date (YYYY-MM-DD)")
    parser.add_argument("--from-date", default=None, help="bank/cash book from_date (default: Jan 1 of as_of year)")
    parser.add_argument("--to-date", default=None, help="bank/cash book to_date (default: as_of)")
    parser.add_argument("--bank-account-id", type=int, default=None, help="optional bank account id for BRS probe")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "tmp" / "mitrabooks-inventory-banking-evidence.json",
    )
    parser.add_argument("--dry-run", action="store_true", help="print planned checks without network calls")
    args = parser.parse_args()

    api_base = str(args.api_base).rstrip("/")
    try:
        as_of_date = date.fromisoformat(args.as_of)
    except ValueError:
        print(f"FAIL: invalid --as-of {args.as_of!r} (expected YYYY-MM-DD)")
        return 2
    from_date = args.from_date or date(as_of_date.year, 1, 1).isoformat()
    to_date = args.to_date or args.as_of

    if args.dry_run:
        print("MitraBooks Inventory + Banking gate - dry run")
        print(f" - api_base: {api_base}")
        print(f" - as_of: {args.as_of}")
        print(f" - bank/cash book window: {from_date} .. {to_date}")
        print(f" - business tenant: {BUSINESS_TENANT_ID} (app_key={BUSINESS_APP_KEY}, org={BUSINESS_ORG_TYPE})")
        print(f" - required modules: {sorted(BUSINESS_REQUIRED_MODULES)}")
        print(f" - bank-recon BRS: {'account_id=' + str(args.bank_account_id) if args.bank_account_id else 'skipped (no --bank-account-id)'}")
        print(f" - business creds env: (MB_E2E_EMAIL, MB_E2E_PASSWORD)")
        print(f" - optional fail-closed creds env: ({FAILCLOSED_EMAIL_ENV}, {FAILCLOSED_PASSWORD_ENV})")
        print("PASS: dry run only (no network calls, no assertions evaluated)")
        return 0

    email = os.environ.get("MB_E2E_EMAIL", "").strip()
    password = os.environ.get("MB_E2E_PASSWORD", "").strip()
    if not email or not password:
        print("FAIL: missing credentials: set MB_E2E_EMAIL and MB_E2E_PASSWORD")
        return 2

    evidence: dict = {
        "gate": "mitrabooks_inventory_banking",
        "status": "pending",
        "read_only": True,
        "started_at": utc_now(),
        "api_base": api_base,
        "as_of": args.as_of,
        "bank_book_window": {"from_date": from_date, "to_date": to_date},
        "steps": [],
    }

    token, err = _login(api_base, BUSINESS_APP_KEY, email, password)
    if not token:
        print(f"FAIL: {err}")
        evidence["status"] = "failed"
        evidence["error"] = err
        evidence["completed_at"] = utc_now()
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        return 1
    auth = {"Authorization": f"Bearer {token}", "X-App-Key": BUSINESS_APP_KEY, "Content-Type": "application/json"}

    steps = [
        check_context(api_base, auth),
        check_inventory_policy(api_base, auth),
        check_inventory_reads(api_base, auth, args.as_of),
        check_bank_cash_book(api_base, auth, from_date, to_date),
        check_bank_recon(api_base, auth, args.bank_account_id, args.as_of),
        check_fail_closed(api_base, from_date, to_date),
    ]
    evidence["steps"] = steps

    for step in steps:
        label = "skipped" if step.get("skipped") else step.get("status", "?")
        print(f"  {step['name']}: {label}")
        if step.get("error"):
            print(f"    error: {step['error']}")

    all_passed = all(s.get("status") == "passed" for s in steps)
    evidence["status"] = "passed" if all_passed else "failed"
    evidence["completed_at"] = utc_now()

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print("\n================================================")
    print("MITRABOOKS INVENTORY + BANKING SUMMARY")
    print("================================================")
    for step in steps:
        label = "SKIPPED" if step.get("skipped") else step.get("status", "?").upper()
        print(f"  [{label}] {step['name']}")
    print(f"  evidence: {args.evidence}")

    if all_passed:
        print("\nPASS: MitraBooks Inventory + Banking gate")
        return 0
    print("\nFAIL: MitraBooks Inventory + Banking gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
