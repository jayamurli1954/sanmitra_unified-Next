# MitraBooks GST/TDS Compliance Review

Date: 2026-09-10 (evidence refresh 2026-09-13)  
Status: **Not signed for production filing** — CA checklist ready; human CA signature open  
Scope: preparation/reporting review of current MitraBooks GST and TDS surfaces.

This review does **not** authorize live GSTN portal filing, IRP e-invoice API calls, e-way bill APIs, or treating GSTN JSON downloads as a filed return.

CA production signoff package: [`MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md`](MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md).

## Verdict

| Claim | Allowed? |
| --- | --- |
| GSTR-1 / GSTR-3B / GSTR-2B / CMP-08 / GSTR-4 are **preparation** reports from posted books | Yes |
| Period GST settlement (ITC set-off, cash payable, carry-forward) posts through the accounting service | Yes, as books settlement — not a GSTN filing |
| GSTN-shaped JSON download for accountant upload to the offline utility | Yes, as a draft the accountant must review |
| Production GST filing, IRP/e-way live APIs, or “returns filed from MitraBooks” | **No** |
| TDS/TCS register as Form 26Q / 27EQ **preparation** | Yes |
| TDS/TCS as filed with the Income-tax portal | **No** |

## Current state (what exists)

Evidence: `app/modules/business/gst_returns.py`, `services/gst_settlement.py`, `services/gst_period_locks.py`, `einvoice.py`, `tds.py`, ERP `gst-returns.js` / `tds.js`, pending-todo Phase 3 GST/TDS real-stack slice (2026-07-03).

| Surface | Current behaviour | Filing semantics |
| --- | --- | --- |
| GSTR-3B | Assembled from posted ledger tax heads + posted invoices/credit notes. GSTN JSON shape. | Preparation. No portal submit. |
| GSTR-1 | Posted sales invoices and credit notes grouped B2B / B2CL / B2CS / CDNR / HSN / DOCS. | Preparation. |
| GSTR-2B | Upload portal JSON; match to booked purchases. | Reconciliation aid. Not auto-accept ITC. |
| CMP-08 / GSTR-4 | Composition dealer route shape; CMP-08 can post books liability. | Preparation. Composition eligibility is tenant-configured, not legally certified. |
| GST settlement | Section 49 / Rule 88A set-off order; preview/post/reverse; period lock. | Books-only. Does not pay GSTN. |
| Period locks | Lock/unlock GST period; reversal validation. | Internal control, not a GSTN freeze. |
| e-Invoice | Readiness checks, INV-01 payload, **manual** IRN recording. | No IRP/GSP credentials. Live IRP deferred. |
| TDS/TCS | FY 2025-26 default section table; per-document override; GST-exclusive TDS base (CBDT 23/2017); TCS 206C(1H) on GST-inclusive consideration (CBDT 17/2020); quarterly register. | Preparation for 26Q/27EQ. No TRACES/NSDL submit. |

UI copy uses “Download GSTN JSON”, not “File return”. Keep that language.

## Gaps that block a signed production filing claim

1. No GSTN / GSP adapter, no filing acknowledgement (ARN), no amendment/original vs revised return workflow.
2. No independent CA/compliance signature yet on [`MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md`](MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md) confirming GSTR-1 tables and 3B 3.1/4/5 match current GSTN schema / offline utility for the live financial year (schema drift risk).
3. Effective-date tax-rate configuration is still a gap-matrix item; rates must not be treated as hard-coded forever. TDS section table is FY 2025-26 defaults with overrides — needs a Finance Act refresh process.
4. E-invoice INV-01 payload uses JSON number encoding required by GSTN (`float` only in the payload assembler, not in the ledger). Live IRP is still deferred.
5. Export JSON governance for GST returns is still a Phase 4 residual (pending todo).
6. ~~Hosted destructive mutation reconfirm after staging credential drift~~ — **closed 2026-09-13**: hosted Phase 3 destructive PASS on `demo-mitrabooks-business` (includes GST/TDS real-stack slice). Evidence: `MITRABOOKS_PHASE3_BUSINESS_WORKFLOW_SIGNOFF.md` Latest Run 2026-09-13.

## What operators may tell tenants

Allowed:

- “MitraBooks prepares GSTR-1 / 3B / 2B / CMP-08 / GSTR-4 from posted invoices and the ledger. Download JSON and review before any portal upload.”
- “GST settlement in MitraBooks sets off ITC in the books. You still pay GST on the portal.”
- “e-Invoice: validate locally, download INV-01, record IRN after the portal issues it.”

Forbidden until a later signed review:

- “MitraBooks files your GST return.”
- “IRN is generated automatically.”
- “TDS is deposited / 26Q is filed from MitraBooks.”

## Signoff

| Role | Result |
| --- | --- |
| Engineering review (this note) | Preparation surfaces exist; filing not enabled |
| Compliance / CA production signoff | **Open** — checklist at [`MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md`](MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md); hosted GST/TDS real-stack evidence current as of 2026-09-13 |
| Live IRP / e-way workstream | Deferred until CA checklist is signed **and** tenant policy exists |

Cross-references: `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md` GST rows, `docs/operations/MITRABOOKS_PENDING_GAP_TODO.md` Phase 3/4 GST `[~]` items, `AGENTS.md` GST preparation-until-review rule.
