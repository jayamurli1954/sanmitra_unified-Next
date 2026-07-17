#!/usr/bin/env python3
"""Guarded GruhaMitra Stage 4 hosted billing gate (generate → post → collect → reverse).

Fail-closed: requires explicit demo-tenant confirmation and never prints tokens/passwords.
Writes sanitized evidence under tmp/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API_BASE = "https://sanmitra-unified-next-staging-sg.onrender.com"
DEFAULT_TENANT_ID = "gruhamitra-demo-society"
DEFAULT_APP_KEY = "gruhamitra"
CONFIRM_ENV = "GRUHA_DEMO_E2E_CONFIRM"
RUN_ENV = "GRUHA_RUN_DESTRUCTIVE_E2E"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout: int = 60,
) -> tuple[int, dict | list]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw or "{}")
            return int(getattr(response, "status", 200)), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            payload = {"detail": raw or exc.reason}
        return int(exc.code), payload


def _detail(payload: dict | list) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("error") or payload.get("message")
        if isinstance(detail, str):
            return detail
        return str(detail or payload)
    return str(payload)


def validate_policy(tenant_id: str, env: dict[str, str] | None = None) -> tuple[bool, list[str]]:
    runtime = os.environ if env is None else env
    errors: list[str] = []
    normalized = str(tenant_id or "").strip()
    if normalized != DEFAULT_TENANT_ID:
        errors.append(f"--demo-tenant-id must be {DEFAULT_TENANT_ID!r}")
    if str(runtime.get(CONFIRM_ENV, "")).strip() != DEFAULT_TENANT_ID:
        errors.append(f"{CONFIRM_ENV} must equal {DEFAULT_TENANT_ID!r}")
    if str(runtime.get(RUN_ENV, "")).strip().lower() not in {"1", "true", "yes"}:
        errors.append(f"{RUN_ENV}=true is required")
    if not str(runtime.get("E2E_USER_EMAIL", "")).strip():
        errors.append("E2E_USER_EMAIL is required")
    if not str(runtime.get("E2E_USER_PASSWORD", "")).strip():
        errors.append("E2E_USER_PASSWORD is required")
    return (not errors), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="GruhaMitra Stage 4 hosted billing gate")
    parser.add_argument("--api-base", default=os.getenv("STAGING_API_BASE_URL", DEFAULT_API_BASE))
    parser.add_argument("--demo-tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--month", type=int, default=7)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--skip-collection", action="store_true")
    parser.add_argument("--skip-reversal", action="store_true")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "tmp" / "gruhamitra-stage4-billing-evidence.json",
    )
    parser.add_argument("--policy-check-only", action="store_true")
    args = parser.parse_args()

    ok, errors = validate_policy(args.demo_tenant_id)
    if not ok:
        print("FAIL: destructive billing policy check failed")
        for err in errors:
            print(f" - {err}")
        return 2
    if args.policy_check_only:
        print("PASS: GruhaMitra Stage 4 destructive billing policy check")
        return 0

    api_base = str(args.api_base).rstrip("/")
    app_key = DEFAULT_APP_KEY
    email = os.environ["E2E_USER_EMAIL"].strip()
    password = os.environ["E2E_USER_PASSWORD"].strip()
    evidence: dict = {
        "gate": "gruhamitra_stage4_billing",
        "status": "pending",
        "started_at": utc_now(),
        "api_base": api_base,
        "app_key": app_key,
        "tenant_id_expected": args.demo_tenant_id,
        "billing_period": {"month": args.month, "year": args.year},
        "steps": {},
    }

    try:
        login_status, login_payload = _request_json(
            "POST",
            f"{api_base}/api/v1/auth/login",
            headers={"Content-Type": "application/json", "X-App-Key": app_key},
            body={"email": email, "password": password},
        )
        if login_status >= 300 or not isinstance(login_payload, dict) or not login_payload.get("access_token"):
            raise RuntimeError(f"login failed HTTP {login_status}: {_detail(login_payload)}")
        token = str(login_payload["access_token"])
        auth = {
            "Authorization": f"Bearer {token}",
            "X-App-Key": app_key,
            "Content-Type": "application/json",
        }

        modules_status, modules_payload = _request_json(
            "GET", f"{api_base}/api/v1/modules/me", headers=auth
        )
        if modules_status >= 300 or not isinstance(modules_payload, dict):
            raise RuntimeError(f"modules/me failed HTTP {modules_status}: {_detail(modules_payload)}")
        tenant_id = str(modules_payload.get("tenant_id") or "").strip()
        org_type = str(modules_payload.get("organization_type") or "").strip().upper()
        if tenant_id != args.demo_tenant_id:
            raise RuntimeError(f"tenant mismatch: got {tenant_id!r}")
        if org_type != "HOUSING":
            raise RuntimeError(f"organization_type mismatch: got {org_type!r}")
        evidence["tenant_id"] = tenant_id
        evidence["organization_type"] = org_type
        evidence["steps"]["auth"] = {"status": "passed"}

        # Preflight: flats exist
        flats_status, flats_payload = _request_json("GET", f"{api_base}/api/v1/flats", headers=auth)
        if flats_status >= 300:
            raise RuntimeError(f"list flats failed HTTP {flats_status}: {_detail(flats_payload)}")
        flats = flats_payload if isinstance(flats_payload, list) else flats_payload.get("items") or flats_payload.get("flats") or []
        if not flats:
            raise RuntimeError("no flats found on demo society; seed flats/members before billing gate")
        evidence["steps"]["flats"] = {"status": "passed", "count": len(flats)}

        # Ensure housing COA exists before posting (idempotent).
        coa_status, coa_payload = _request_json(
            "POST",
            f"{api_base}/api/v1/accounting/initialize-chart-of-accounts",
            headers=auth,
        )
        if coa_status >= 300 or not isinstance(coa_payload, dict):
            raise RuntimeError(
                f"initialize-chart-of-accounts failed HTTP {coa_status}: {_detail(coa_payload)}"
            )
        evidence["steps"]["initialize_coa"] = {
            "status": "passed",
            "accounts_created": coa_payload.get("accounts_created"),
            "accounts_existing": coa_payload.get("accounts_existing"),
            "total_accounts": coa_payload.get("total_accounts"),
        }

        bills_qs = urlencode({"month": args.month, "year": args.year})
        bills_status, bills_payload = _request_json(
            "GET", f"{api_base}/api/v1/maintenance/bills?{bills_qs}", headers=auth
        )
        existing_bills = bills_payload if isinstance(bills_payload, list) else []
        unposted = [
            b for b in existing_bills
            if not b.get("is_posted") and str(b.get("status") or "").lower() != "reversed"
        ]

        if unposted:
            evidence["steps"]["generate"] = {
                "status": "skipped",
                "reason": "unposted bills already exist for period",
                "total_bills": len(unposted),
            }
        else:
            # Generate bills (async job)
            gen_status, gen_payload = _request_json(
                "POST",
                f"{api_base}/api/v1/maintenance/generate-bills",
                headers=auth,
                body={"month": args.month, "year": args.year},
            )
            if gen_status >= 300 or not isinstance(gen_payload, dict):
                raise RuntimeError(f"generate-bills failed HTTP {gen_status}: {_detail(gen_payload)}")
            job_id = str(gen_payload.get("job_id") or "").strip()
            if not job_id:
                raise RuntimeError(f"generate-bills missing job_id: {gen_payload}")
            evidence["steps"]["generate"] = {
                "status": "started",
                "job_id": job_id,
                "total_flats": gen_payload.get("total_flats"),
            }

            job: dict = {}
            for _ in range(60):
                time.sleep(2)
                job_status, job_payload = _request_json(
                    "GET",
                    f"{api_base}/api/v1/maintenance/billing-jobs/{job_id}",
                    headers=auth,
                )
                if job_status >= 300 or not isinstance(job_payload, dict):
                    raise RuntimeError(f"billing job poll failed HTTP {job_status}: {_detail(job_payload)}")
                job = job_payload
                status = str(job.get("status") or "").lower()
                if status in {"completed", "failed"}:
                    break
            if str(job.get("status") or "").lower() != "completed":
                raise RuntimeError(
                    f"billing job did not complete: status={job.get('status')} error={job.get('error')}"
                )
            evidence["steps"]["generate"] = {
                "status": "passed",
                "job_id": job_id,
                "total_bills": job.get("total_bills"),
                "total_amount": job.get("total_amount"),
            }

        bills_status, bills_payload = _request_json(
            "GET", f"{api_base}/api/v1/maintenance/bills?{bills_qs}", headers=auth
        )
        if bills_status >= 300 or not isinstance(bills_payload, list):
            raise RuntimeError(f"list bills failed HTTP {bills_status}: {_detail(bills_payload)}")
        if not bills_payload:
            raise RuntimeError("no bills available for period after generate")
        evidence["steps"]["list_bills"] = {
            "status": "passed",
            "count": len(bills_payload),
            "sample_flat": bills_payload[0].get("flat_number"),
            "sample_amount": bills_payload[0].get("amount"),
        }

        # Post bills to accounting
        post_status, post_payload = _request_json(
            "POST",
            f"{api_base}/api/v1/maintenance/post-bills",
            headers=auth,
            body={"month": args.month, "year": args.year},
        )
        if post_status >= 300 or not isinstance(post_payload, dict):
            raise RuntimeError(f"post-bills failed HTTP {post_status}: {_detail(post_payload)}")
        posted_count = int(post_payload.get("total_bills_generated") or 0)
        journal_ids = post_payload.get("posted_journal_entries") or []
        if posted_count < 1 or not journal_ids:
            raise RuntimeError(f"post-bills returned no journals: {post_payload}")
        evidence["steps"]["post_bills"] = {
            "status": "passed",
            "posted_count": posted_count,
            "journal_entry_ids": journal_ids[:20],
            "journal_entry_count": len(journal_ids),
        }

        # Accounting evidence: voucher drilldown for first journal
        first_journal = int(journal_ids[0])
        voucher_status, voucher_payload = _request_json(
            "GET",
            f"{api_base}/api/v1/accounting/reports/vouchers/{first_journal}",
            headers=auth,
        )
        if voucher_status >= 300 or not isinstance(voucher_payload, dict):
            raise RuntimeError(
                f"voucher drilldown failed HTTP {voucher_status}: {_detail(voucher_payload)}"
            )
        lines = voucher_payload.get("lines") or voucher_payload.get("journal_lines") or []
        debit_total = 0.0
        credit_total = 0.0
        for line in lines if isinstance(lines, list) else []:
            debit_total += float(line.get("debit") or line.get("debit_amount") or 0)
            credit_total += float(line.get("credit") or line.get("credit_amount") or 0)
        balanced = abs(debit_total - credit_total) < 0.005
        if not balanced:
            raise RuntimeError(f"journal {first_journal} unbalanced: debit={debit_total} credit={credit_total}")
        evidence["steps"]["accounting_evidence"] = {
            "status": "passed",
            "journal_entry_id": first_journal,
            "line_count": len(lines) if isinstance(lines, list) else 0,
            "debit_total": round(debit_total, 2),
            "credit_total": round(credit_total, 2),
            "balanced": True,
        }

        # Reload posted bills
        bills_status, bills_payload = _request_json(
            "GET", f"{api_base}/api/v1/maintenance/bills?{bills_qs}", headers=auth
        )
        posted_bills = [
            b for b in (bills_payload if isinstance(bills_payload, list) else [])
            if b.get("is_posted") or str(b.get("status") or "").lower() == "posted"
        ]
        if not posted_bills:
            raise RuntimeError("no posted bills after post-bills")
        sample = posted_bills[0]

        if not args.skip_collection:
            amount = float(sample.get("amount") or 0)
            if amount <= 0:
                raise RuntimeError("sample bill amount is not positive")
            collect_status, collect_payload = _request_json(
                "POST",
                f"{api_base}/api/v1/housing/maintenance-collections",
                headers=auth,
                body={
                    "amount": f"{amount:.2f}",
                    "bill_id": sample.get("id"),
                    "flat_number": sample.get("flat_number"),
                    "payment_mode": "bank",
                    "collected_on": date.today().isoformat(),
                    "reference": "stage4-demo-collection",
                },
            )
            if collect_status >= 300 or not isinstance(collect_payload, dict):
                raise RuntimeError(
                    f"maintenance-collections failed HTTP {collect_status}: {_detail(collect_payload)}"
                )
            evidence["steps"]["collection"] = {
                "status": "passed",
                "collection_id": collect_payload.get("collection_id"),
                "journal_entry_id": collect_payload.get("journal_entry_id"),
                "bill_id": collect_payload.get("bill_id"),
                "bill_status": collect_payload.get("bill_status"),
                "amount": collect_payload.get("amount"),
            }

        if not args.skip_reversal and len(posted_bills) > 1:
            reverse_target = posted_bills[1]
            rev_status, rev_payload = _request_json(
                "POST",
                f"{api_base}/api/v1/maintenance/reverse-bill",
                headers=auth,
                body={
                    "bill_id": reverse_target.get("id"),
                    "reversal_reason": "Stage4 demo reversal evidence only",
                },
            )
            if rev_status >= 300 or not isinstance(rev_payload, dict):
                raise RuntimeError(f"reverse-bill failed HTTP {rev_status}: {_detail(rev_payload)}")
            evidence["steps"]["reversal"] = {
                "status": "passed",
                "bill_id": reverse_target.get("id"),
                "reversal_journal_entry_id": rev_payload.get("reversal_journal_entry_id"),
                "status_result": rev_payload.get("status"),
            }
        elif not args.skip_reversal:
            evidence["steps"]["reversal"] = {
                "status": "skipped",
                "reason": "only one posted bill available; collection kept for dues evidence",
            }

        evidence["status"] = "passed"
        evidence["completed_at"] = utc_now()
    except Exception as exc:
        evidence["status"] = "failed"
        evidence["error"] = str(exc)
        evidence["completed_at"] = utc_now()
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(f"FAIL: {exc}")
        print(f"Evidence: {args.evidence}")
        return 1

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("PASS: GruhaMitra Stage 4 hosted billing gate")
    print(f" - tenant_id: {evidence.get('tenant_id')}")
    print(f" - period: {args.month}/{args.year}")
    print(f" - generate bills: {evidence['steps'].get('generate', {}).get('total_bills')}")
    print(f" - posted journals: {evidence['steps'].get('post_bills', {}).get('journal_entry_count')}")
    print(f" - accounting balanced: {evidence['steps'].get('accounting_evidence', {}).get('balanced')}")
    print(f" - collection: {evidence['steps'].get('collection', {}).get('status')}")
    print(f" - reversal: {evidence['steps'].get('reversal', {}).get('status')}")
    print(f" - evidence: {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
