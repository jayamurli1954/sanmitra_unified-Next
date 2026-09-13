# MitraBooks GST/TDS — CA / filing production signoff checklist

**Product:** MitraBooks ERP  
**Tenant for evidence:** `demo-mitrabooks-business` only (staging)  
**Authority:** [`MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md`](MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md)  
**Related:** Phase 3 destructive gate (`frontend/e2e/mitrabooks-realstack-destructive.spec.js`), Track 0 credentials runbook

## Scope (non-negotiable)

This checklist can authorize **preparation / reporting readiness** for an accountant to download MitraBooks GSTN-shaped JSON and TDS registers, review them, and upload **manually** through government offline utilities / portals.

It does **not** authorize:

- Live GSTN / GSP filing from MitraBooks
- Automatic IRN generation / live IRP or e-way APIs
- Claiming “returns filed from MitraBooks”
- Claiming TDS deposited / 26Q–27EQ filed from MitraBooks

UI language must remain “Download GSTN JSON” / preparation — never “File return”.

## Preconditions

1. Engineering compliance review exists and still labels surfaces as preparation-only.
2. Hosted destructive real-stack GST/TDS slice has a **current** PASS on `demo-mitrabooks-business` (see evidence table).
3. Operator uses staging demo credentials from the secret manager only (`TRACK0_STAGING_CREDENTIALS_RUNBOOK.md`). Do not commit passwords.
4. No production tenant mutation.

## Engineering evidence already on record

| Evidence | Status | Pointer |
| --- | --- | --- |
| Engineering compliance review (prep vs filing) | PASS 2026-09-10 | `MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md` |
| Local + real-stack GST/TDS demo mutation (TCS/TDS docs → GSTR-3B → GSTR-1/CDNR → GSTR-2B recon → CMP-08/GSTR-4 → settlement post/reverse → period lock) | PASS (in Phase 3 destructive gate) | `MITRABOOKS_PHASE3_BUSINESS_WORKFLOW_SIGNOFF.md` |
| Hosted destructive reconfirm after credential drift | PASS 2026-09-13 | Phase 3 signoff Latest Run 2026-09-13 |
| Live IRP / e-way | Deferred | Gap matrix / compliance review |

## CA review — preparation readiness

Complete against a **current FY period** with posted demo invoice/bill/credit-note (or a CA-owned sandbox tenant with the same feature flags). Prefer regenerating JSON from hosted staging after a guarded destructive run, then reviewing downloads offline.

| # | Check | Pass? | Reviewer initials / date | Notes |
| --- | --- | --- | --- | --- |
| C1 | Tenant GST profile (GSTIN, place of supply, composition flag) is visible and matches the books under review | | | |
| C2 | GSTR-1 JSON: B2B / B2CL / B2CS / CDNR / HSN / DOCS sections present; amounts reconcile to posted sales invoices + credit notes for the period | | | |
| C3 | GSTR-3B JSON: 3.1 / 4 / 5 style liability and ITC figures reconcile to posted output tax and eligible input for the period (within documented settlement rules) | | | |
| C4 | GSTR-2B reconcile: uploaded portal sample matches booked purchases without auto-accepting ITC | | | |
| C5 | CMP-08 / GSTR-4: route shape usable for composition tenants; liability posting (if used) is books-only and reversible | | | |
| C6 | GST settlement preview/post/reverse: Section 49 / Rule 88A set-off order understood; cash payable is **not** treated as GSTN payment | | | |
| C7 | Period lock/unlock: locked period blocks unauthorized GST mutations; unlock requires admin and is audited | | | |
| C8 | e-Invoice: INV-01 download + manual IRN record only; no live IRP credential path enabled | | | |
| C9 | TDS register (quarter): section, base (GST-exclusive per CBDT 23/2017), and payable lines suitable as **26Q preparation**; TCS lines (if any) suitable as **27EQ preparation** | | | |
| C10 | UI / operator docs never claim MitraBooks filed the return or deposited TDS | | | |
| C11 | Schema drift: reviewer confirms downloaded JSON opens in the **current** GSTN offline utility (or equivalent CA tool) for the live FY without structural rejection | | | |
| C12 | Known residuals accepted as **out of scope** for this signoff: live GSTN/GSP adapter, ARN workflow, amendments, effective-date rate master polish, live IRP/e-way | | | |

## Operator commands (staging demo only)

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="business.admin@sanmitra.local"
$env:E2E_USER_PASSWORD="<staging-only secret>"
python scripts/verify_staging_auth.py
# Optional: re-run guarded GST-inclusive destructive mutation for fresh JSON sources
# (requires MITRABOOKS_RUN_DESTRUCTIVE_E2E via the Phase 3 gate helpers)
```

Do not paste passwords into this checklist or into git.

## Signoff block

| Role | Name | Date | Result |
| --- | --- | --- | --- |
| Engineering (prep surfaces + evidence pointers) | | | Preparation-only confirmed; live filing not enabled |
| Compliance / CA (this checklist C1–C12) | | | **Open until signed** |
| Platform owner (optional) | | | |

### Allowed claim after CA signs C1–C12

> MitraBooks prepares GSTR-1 / GSTR-3B / GSTR-2B / CMP-08 / GSTR-4 and TDS/TCS registers from posted books. Accountants may download JSON/registers, review, and file manually on government portals. MitraBooks does not file returns or deposit tax.

### Forbidden claims (still)

> MitraBooks files GST returns / generates IRN automatically / deposits TDS / files 26Q–27EQ.

## Status log

| Date | Event |
| --- | --- |
| 2026-09-10 | Engineering compliance review: preparation-only; CA signoff open |
| 2026-09-13 | Hosted Phase 3 destructive mutation reconfirmed PASS on `demo-mitrabooks-business` (includes GST/TDS real-stack slice) |
| 2026-09-13 | This CA checklist created; **human CA signature still required** |
