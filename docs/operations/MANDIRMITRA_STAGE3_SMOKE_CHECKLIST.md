# MandirMitra Stage 3 Smoke Checklist

## Purpose

This checklist is the repeatable live-readiness gate for MandirMitra inside the MitraBooks ERP shell.

Use it after focused automated checks pass and before calling MandirMitra live-ready. The checklist intentionally covers only MandirMitra and the MitraBooks accounting/shell foundation needed by MandirMitra. Broader MitraBooks business ERP scope remains deferred until MandirMitra and GruhaMitra are live.

## Automated Smoke

Run from `D:\sanmitra_unified-Next`:

```powershell
python scripts\mandirmitra_stage3_smoke.py
```

Expected result:

- Python compile checks pass for accounting, MandirMitra compatibility, tenant/module context, and scripts.
- Focused pytest suites pass for MandirMitra posting, receipt terminology, report routes, accounting drill-down, app-key isolation, tenant lifecycle, modules/me, module access, and platform-owner dashboard where the test files exist.

## Browser Smoke

Install once if needed:

```powershell
pip install playwright
python -m playwright install chromium
```

With the backend and frontend running, run from `D:\sanmitra_unified-Next`:

```powershell
python scripts\mandirmitra_stage3_browser_smoke.py
```

Expected result:

- Local login succeeds with `X-App-Key: mandirmitra`.
- `/api/v1/modules/me` returns `organization_type=TEMPLE` with `temple`, `accounting`, and `audit`.
- The MitraBooks ERP shell opens in MandirMitra mode.
- Visible UI includes MandirMitra, Donations, Sevas, Public Payments, Receipts, Panchang, Reports, and Trial Balance.
- The Public Payments workspace exposes an `Open Public Page` link for non-auth devotee-facing visibility checks.
- The Receipts workspace shows cancellation/reversal action for active receipts and opens the cancellation dialog without mutating data during smoke.
- The Panchang workspace opens and renders Today Panchang with Tithi data from `/api/v1/panchang/today`.
- The Reports workspace opens and renders donation category, detailed donation, detailed seva, seva schedule, and recent devotee data.
- The UI does not show access denied or MandirMitra live-data-unavailable state.
- A screenshot is saved under `tmp\mandir-stage3-browser-smoke.png`.

Latest local evidence on 2026-05-22:

- GitHub CI was green for the latest MandirMitra commits.
- Render workflow deployed and was green.
- Local browser/backend smoke passed with `python scripts\mandirmitra_stage3_browser_smoke.py --api-base http://127.0.0.1:8001`.
- Local cancellation/reversal was verified on seed/demo local data only: `DON-0000004` was marked `reversed`, `REV-112-DON-0000004` appeared in drill-down, Trial Balance remained balanced at `Rs. 1,715.00`, and I&E, R&P, and Balance Sheet remained consistent.

Latest staging/non-destructive evidence on 2026-05-22:

- GitHub CI was green.
- Render deployment completed green.
- MandirMitra login/module context loaded with `organization_type=TEMPLE` and `temple`, `accounting`, and `audit`.
- MandirMitra tabs loaded, receipt preview/download worked, Panchang opened, reports opened, and accounting reports opened and balanced.
- Public no-login visibility passed through `/mandir-public/`: the page loaded without login, listed the public-enabled temple/trust, displayed public UPI/config visibility, showed donation purpose selection, and generated UPI intent preview without creating a payment.
- The active visible public tenant was Parlathya Prathishtana, so the staging result is non-destructive/read-config-only. No donation creation, cancellation, refund, or reversal was performed on that real trust tenant.
- Follow-up code removes automatic startup public-UPI seeding for the real Parlathya record. Destructive staging checks must use the explicit demo Mandir bootstrap tenant (`DEMO_MANDIR_TENANT_ID`, default `demo-mandir-tenant`) with demo UPI/config values.

## Local Services

Backend:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
python scripts\serve_frontends.py --host 127.0.0.1 --port 3300
```

Open:

```text
http://127.0.0.1:3300/mitrabooks-erp/#
```

Known local login:

```text
admin@sanmitra.local / admin123
```

## Stage 3 Live Checks

Record pass/fail evidence for each item.

| Area | Check | Expected result | Evidence |
| --- | --- | --- | --- |
| Login | Login as MandirMitra tenant admin | ERP shell opens without access denied |  |
| Module context | Call or observe `/api/v1/modules/me` | `organization_type=TEMPLE`; enabled modules include `temple`, `accounting`, `audit`; active app key is `mandirmitra` |  |
| Navigation | Open MandirMitra overview, donations, sevas, public payments, exceptions, receipts, accounting/reports | Tabs/panels load tenant-scoped data only |  |
| Public payment | Open no-login public devotee flow | Devotee can select temple/trust, choose donation or seva, enter details/amount, and see the selected tenant's configured UPI/payment instructions |  |
| Public page visibility | Open `/mandir-public/` or the ERP `Open Public Page` link | Page loads without login, lists public-enabled temples, and displays public UPI/config/seva/category visibility without creating a payment |  |
| Staging tenant safety | Confirm whether the active tenant is demo/test or real trust data | Destructive tests such as donation creation, cancellation, refund, or reversal are allowed only on demo/test tenants; real temple/trust tenants are non-destructive verification only |  |
| Donation | Create a donation | Donation record saves, receipt number is stable, accounting posting succeeds |  |
| Donation PDF | Preview/download donation receipt | Title is `ದೇಣಿಗೆ ರಶೀದಿ / Donation Receipt`; donation term is `ದೇಣಿಗೆ`; receipt spelling is `ರಶೀದಿ`; temple label uses `ದೇವಸ್ಥಾನ`; no seva-only note/signature block |  |
| Seva | Create a seva booking | Seva booking saves, receipt number is stable, accounting posting succeeds |  |
| Seva PDF | Preview/download seva receipt | Title is `ಸೇವಾ ರಶೀದಿ / Seva Receipt`; uses `ಭಕ್ತ / Devotee`; includes `ಈ ಕೆಳಗೆ ಕಾಣಿಸಿದ ಸೇವೆಯ ಸಲುವಾಗಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ` |  |
| Expense | Create a MandirMitra expense | Expense voucher posts through shared accounting and appears in expense section only |  |
| Trial Balance | Open Trial Balance after donation, seva, and expense | Total debit equals total credit |  |
| Voucher drill-down | Open Trial Balance row and voucher detail | Month/week/day/voucher drill-down works; voucher shows debit and credit lines |  |
| Income and Expenditure | Open report | Donation/seva income and expenses match posted vouchers |  |
| Receipts and Payments | Open report | Cash/bank receipts and payments match posted vouchers |  |
| Balance Sheet | Open report | Report remains balanced and matches posted vouchers |  |
| Receipt cancellation/reversal | Cancel a demo/test donation or seva receipt | Original receipt remains immutable; receipt status becomes `reversed`; linked `REV-*` journal appears in drill-down; repeated cancellation is idempotent or disabled in UI; Trial Balance remains balanced |  |
| Exceptions | Verify, reject, and correct pending public payments where test data exists | Verification posts only after UTR/reference capture; rejection/correction retains audit trail |  |
| Receipt history | Open donation/seva receipt history | Recent receipts list with preview/download actions |  |
| Tenant isolation | Try MandirMitra data from GruhaMitra/MitraBooks app context | Cross-app access fails closed or returns only allowed scoped data |  |
| Accounting guardrail | Review posting path for created records | No direct ledger/balance mutation; posting goes through shared accounting service |  |
| Audit | Review audit trail where implemented | Verification, rejection, correction, tenant/module changes, and financial actions are traceable |  |
| Deployment readiness | Review env, seed/demo tenant assumptions, rollback notes, and staging deployment | No local-only assumptions block staging/live deployment |  |

## Signoff Rule

MandirMitra is not live-ready until:

- Automated smoke passes.
- All Stage 3 live checks above are pass or explicitly marked not applicable with reason.
- Donation, seva, and expense transactions reconcile through Trial Balance, voucher drill-down, Income and Expenditure, Receipts and Payments, and Balance Sheet.
- Receipt PDF terminology and layout are visually confirmed.
- Public no-login payment flow is verified for at least one configured temple/trust.
- Tenant/app isolation and accounting guardrails have no open blocker.

## Staging Rule

- Use non-destructive staging checks unless a clearly marked demo/test temple tenant is available.
- Do not create, cancel, refund, reverse, or otherwise mutate receipts for real temple/trust tenants such as Parlathya Prathishtana.
- If no staging demo tenant exists, mark mutation checks as blocked by seed/demo policy and complete only login, module context, navigation, report, PDF preview, and public no-login read/config checks.
- As of 2026-05-22, the staging smoke is passed for non-destructive checks; destructive mutation checks remain blocked until a clearly marked demo/test temple tenant is available.
- Demo mutation checks require `DEMO_MANDIR_BOOTSTRAP=true` and a staging-only `DEMO_MANDIR_ADMIN_PASSWORD`. The demo tenant public page should show demo payee/UPI values, not a real trust account.
