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
| Reference tenant | Validate Parlathya Prathishtana public payment behavior if configured locally/staging | Temple/trust selection and payment instructions match known working behavior |  |
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
