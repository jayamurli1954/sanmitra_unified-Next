# Track 0 GruhaMitra Staging Credentials Runbook

## Purpose

Add-on Track 0 gate for GruhaMitra Stage 4 hosted staging E2E. Use this when Ops enables the
staging demo housing society tenant. Do not rewrite
`docs/operations/TRACK0_STAGING_CREDENTIALS_RUNBOOK.md` (MitraBooks) or
`docs/operations/TRACK0_MANDIR_STAGING_CREDENTIALS_RUNBOOK.md` (MandirMitra).

This runbook defines auth precheck and guarded mutation rules without committing secrets.

## Scope

- Applies only to an explicit demo/test/seed housing tenant on hosted staging.
- Default demo tenant id: `gruhamitra-demo-society`
- App key: `gruhamitra`
- Organization type: `HOUSING`
- Required modules: `housing`, `accounting`, `audit`
- Never mutate a real client housing society.
- Do not store plaintext credentials in repo files, screenshots, traces, or CI logs.

Cross-links:

- Checklist: `docs/operations/GRUHAMITRA_STAGE4_SMOKE_CHECKLIST.md`
- Stage flow: `docs/operations/STAGED_E2E_PLAN.md` (Stage 4 GruhaMitra)
- Seed helper: `scripts/seed_gruhamitra_demo.py`
- Auth precheck: `scripts/verify_staging_auth.py`

## Prerequisite

MandirMitra Stage 3 machine signoff must be accepted (or an explicit platform-owner waiver for
Stage 4 start). As of 2026-07-17: `verify_mandirmitra_stage3_signoff.py` PASSED for
`backend-v1.3.0` / rollback `backend-v1.2.0`.

## Hosted Targets

| Role | URL |
| --- | --- |
| Frontend (GruhaMitra) | `https://www.gruhamitra.sanmitratech.in/gruhamitra/` |
| Frontend (MitraBooks ERP shell, if used) | `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |
| Staging API | `https://sanmitra-unified-next-staging-sg.onrender.com` |

## Operator Session Setup (No Secret Commit)

Set variables only in the operator shell. Obtain passwords from the secret manager or the
authorized demo-seed operator notes — do not paste them into git or chat evidence.

```powershell
$env:STAGING_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:STAGING_APP_KEY = "gruhamitra"
$env:EXPECTED_TENANT_ID = "gruhamitra-demo-society"
$env:EXPECTED_ORGANIZATION_TYPE = "HOUSING"
$env:REQUIRED_MODULES = "housing,accounting,audit"
$env:E2E_USER_EMAIL = "<staging demo admin email>"
$env:E2E_USER_PASSWORD = "<staging-only password from secret manager>"

python scripts/verify_staging_auth.py
```

Expected sanitized output:

- `tenant_id=gruhamitra-demo-society`
- `organization_type=HOUSING`
- enabled modules include `housing`, `accounting`, `audit`

Do not use a raw `curl` login response as signoff evidence; it prints the access token.

## Seed / Reset (local or staging with approval)

When the demo tenant is missing on an authorized environment:

```powershell
python scripts/seed_gruhamitra_demo.py --admin-password "<from secret manager>" --resident-password "<from secret manager>"
```

Never commit the password arguments. Prefer Render env / secret manager for hosted staging.

## Guarded Destructive Rules

1. Run `python scripts/verify_staging_auth.py` with the GruhaMitra env block above first.
2. Confirm the tenant id is visibly demo/test/seed (`gruhamitra-demo-society` or equivalent).
3. Maintenance bill generate/post/collection mutations must target only that demo tenant.
4. Accounting checks: balanced journals, no direct balance mutation, reversals only for corrections.
5. Agents must follow `AGENTS.md` §5 for destructive-E2E commands.

Confirmation string format when a destructive gate script is used:

```text
DESTROY_DEMO_ONLY:<demo-tenant-id>@<api-origin>
```

Example:

```text
DESTROY_DEMO_ONLY:gruhamitra-demo-society@https://sanmitra-unified-next-staging-sg.onrender.com
```

## Stage 4 Remaining Gaps (billing)

Hosted billing cycle on `gruhamitra-demo-society` **PASSED** on 2026-07-17
(`scripts/gruhamitra_stage4_billing_gate.py`, evidence
`tmp/gruhamitra-stage4-billing-evidence.json`):

- Generate maintenance bills (Jul 2026, 9 bills)
- Initialize housing COA when missing, then post through MitraBooks accounting
- Verify debit=credit on voucher drilldown
- Collections/receipts via `/api/v1/housing/maintenance-collections`
- Reversal/adjustment via `/api/v1/maintenance/reverse-bill`

Guarded command (operator shell only; no secrets in git):

```powershell
$env:GRUHA_DEMO_E2E_CONFIRM = "gruhamitra-demo-society"
$env:GRUHA_RUN_DESTRUCTIVE_E2E = "true"
$env:E2E_USER_EMAIL = "<staging demo admin email>"
$env:E2E_USER_PASSWORD = "<staging-only password from secret manager>"
python scripts/gruhamitra_stage4_billing_gate.py --month 7 --year 2026
```
