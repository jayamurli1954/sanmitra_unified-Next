# ITC Reversal Tracking (GST Rule 37)

> **Status:** ✅ Implemented and verified on branch `feat/itc-reversal-rule37`
> (commit `e4c39463`). 7 new unit tests + a full real-stack E2E (13/13 checks)
> pass. Not yet pushed to `main`/`develop`.
>
> **Reference:** Input Tax Credit overview — https://gstzen.in/a/what-is-input-tax-credit-itc.html

## Context

MitraBooks ERP now has the full GST cycle (Bills → Invoices → Credit/Debit Notes
→ Settlement → Period Lock → Reports). One statutory gap remained: **GST Rule 37**.
When a buyer does not pay a supplier the invoice value **+ tax within 180 days**,
the input tax credit (ITC) already availed on that purchase bill **must be reversed**
(added back to the output liability) **with 18% p.a. interest**. The credit can later
be **reclaimed** once payment is made (interest is not reclaimable).

Previously the system had no way to know whether a bill was paid (vouchers only carry
a `party_id`, with no bill allocation), so nothing flagged overdue bills and no reversal
entry was posted. This change adds lightweight **bill payment tracking**, an **auto-flag
scanner** for bills overdue past 180 days, and **reversal + reclaim postings** that flow
through the existing double-entry ledger and the GST settlement engine. Outcome: a CA/owner
can review flagged bills, post the Rule 37 reversal (with interest), and reclaim the credit
on later payment — all reconciling in the existing reports and settlement.

### Decisions locked with user

1. **Payment source** → add `payment_status` / `paid_amount` / `paid_date` to bills + a
   "Mark as paid" action; scanner auto-flags from these.
2. **Reversed ITC treatment** → park as a **recoverable current asset** (off P&L), reverse
   back on reclaim.
3. **Interest** → compute **and post** 18% p.a. interest alongside the reversal.

## Architecture facts (reused, not rebuilt)

- Business docs live in **MongoDB** (`business_purchase_bills`); only the ledger is Postgres.
  **No migrations.**
- All postings go through `post_journal_entry` (`app/accounting/service.py`).
- `initialize_default_chart_of_accounts` is **idempotent** and inserts only missing codes —
  existing tenants get new accounts on their next bill/settlement create (verified:
  `app/accounting/service.py:603-629`).
- `_gst_period_balances` reads Input GST codes `14001/14002/14003`; **crediting Input GST in
  the reversal period automatically raises that period's net payable in settlement** — so the
  reversal needs no special settlement wiring. Reclaim (debit Input GST) restores it symmetrically.
- Admin gating: `require_roles([Role.super_admin, Role.tenant_admin])` (see `router.py:1029`).
- `is_gst_period_locked` / `_period_key` / `_period_label` guard postings into finalised months.
- Frontend is one `type="module"` ES file; all interactivity via `data-business-action`
  delegation. Compliance tabs live in `BUSINESS_REPORT_TABS` (`app.js:4999`); GST Settlement is
  the reference pattern (`renderGstSettlementPanel`, `loadGstSettlementPreview`, `postGstSettlement`).

## New chart-of-accounts entries

Added to `DEFAULT_BUSINESS_CHART_OF_ACCOUNTS` (`app/accounting/service.py:214`):

- `14004` — **"ITC Reversed – Rule 37 (Recoverable)"** — asset / personal (parking account).
- `23003` — **"Interest Payable on GST"** — liability / personal, `is_payable=True`.
- `54006` — **"Interest on GST"** — expense / nominal.

## Backend — `app/modules/business/service.py`

### Constants

```
ITC_REVERSAL_RECOVERABLE_CODE = "14004"
GST_INTEREST_PAYABLE_CODE     = "23003"
GST_INTEREST_EXPENSE_CODE     = "54006"
ITC_REVERSAL_DAYS  = 180
ITC_INTEREST_RATE  = Decimal("0.18")
```

### Bill doc — new fields (defaults applied lazily in response helper)

`payment_status` ("unpaid"|"partial"|"paid", default "unpaid"), `paid_amount` (str, "0"),
`paid_date` (ISO|null), `itc_reversed` (bool), `itc_reversal_journal_entry_id`,
`itc_reversal_date`, `itc_reversal_period`, `itc_reversed_amounts` ({cgst,sgst,igst}),
`itc_interest_amount`, `itc_reclaimed` (bool), `itc_reclaim_journal_entry_id`, `itc_reclaim_date`.
`_bill_response_doc` `setdefault`s these so existing bills render cleanly.

### New functions

1. **`mark_bill_payment(...)`** — set `paid_amount` / `paid_date`; derive `payment_status`
   (`paid` when `paid_amount >= bill_total`, else `partial`/`unpaid`). Validate
   `0 < paid_amount <= bill_total`; only `status == "posted"` bills. Audit `business_bill_payment_updated`.
2. **`_itc_split_for_bill(bill)`** — return `{cgst,sgst,igst}` Decimals from stored bill totals;
   `itc_total = sum`.
3. **`_compute_itc_interest(itc_total, bill_date, as_of)`** — `itc_total * 0.18 * days/365`,
   `days = (as_of - bill_date).days`, `quantize(0.01, ROUND_HALF_UP)`.
4. **`preview_itc_reversals(..., as_of)`** — scan `business_purchase_bills` where `status=="posted"`,
   `itc_reversed` not true, `gst_total>0`, `payment_status!="paid"`, and `bill_date + 180d <= as_of`.
   Per bill: bill no/vendor/date, `due_date = bill_date+180d`, `days_overdue`, itc split + total,
   computed interest, payment_status, `gstr3b_ref="4(B)(2)"`. Includes grand totals. Read-only.
5. **`reverse_itc_for_bill(session, bill_id, reversal_date, ...)`** — guard `itc_reversed`
   (idempotent), period-lock check on `reversal_date`. Posts one balanced journal:
   - Dr `14004` itc_total; Cr `14001/14002/14003` per head (reduces ITC → settlement picks up).
   - If interest>0: Dr `54006` interest; Cr `23003` interest.
   Idempotency `itc-reversal:{bill_id}`. Updates bill fields; audit `business_itc_reversed`.
6. **`reclaim_itc_for_bill(session, bill_id, reclaim_date, ...)`** — require
   `itc_reversed and not itc_reclaimed and payment_status=="paid"`; period-lock check. Posts:
   Dr `14001/14002/14003` per head; Cr `14004` itc_total (restores ITC; `gstr3b_ref="4(D)(1)"`).
   Idempotency `itc-reclaim:{bill_id}`. Updates fields; audit `business_itc_reclaimed`.

All four call `initialize_default_chart_of_accounts` first (mitrabooks) so the new codes exist,
mirroring `create_purchase_bill`.

## Backend — schemas & router

`app/modules/business/schemas.py`: `BillPaymentUpdateRequest`, `ItcReversalActionRequest`,
`ItcReclaimActionRequest`, response models (`ItcReversalCandidate`, `ItcReversalPreviewResponse`,
reuse `PurchaseBillResponse` for action results).

`app/modules/business/router.py` (mirror settlement/bill endpoints, same context resolution + error mapping):

- `POST /bills/{bill_id}/payment` → `mark_bill_payment` (standard auth).
- `GET  /itc-reversals/preview?as_of=YYYY-MM-DD` → `preview_itc_reversals` (standard auth, read-only).
- `POST /bills/{bill_id}/itc-reversal` → `reverse_itc_for_bill` (**admin-gated**).
- `POST /bills/{bill_id}/itc-reclaim` → `reclaim_itc_for_bill` (**admin-gated**).

## Frontend — `frontend/mitrabooks-erp/app.js`

- Tab `{ id: "itc-reversals", label: "ITC Reversals" }` in `BUSINESS_REPORT_TABS` (after `gst-settlement`);
  branch in `refreshCurrentBusinessReport` + render switch.
- `loadItcReversalPreview(asOf)` + `renderItcReversalPanel()` mirroring the settlement pattern:
  as-of date input, flagged-bills table (bill, vendor, bill date, 180d due date, days overdue, ITC,
  18% interest, payment status, GSTR-3B ref), per-row **Reverse ITC** (admin) and a "Reversed —
  awaiting reclaim" section with **Reclaim ITC** for reversed+paid bills.
- New `data-business-action` handlers: `itc-preview`, `itc-reverse`, `itc-reclaim`, `bill-mark-paid`
  (bill id via `data-bill-id`). No inline `onclick`.

## Tests — `tests/test_business_phase2.py`

- `test_mark_bill_payment_sets_status` — partial then full → `paid`.
- `test_itc_reversal_candidate_detected_after_180_days` — bill dated >180d, unpaid → appears;
  paid/within-180d/already-reversed/no-ITC excluded.
- `test_itc_reversal_posts_balanced_entry_with_interest` — Dr 14004 + Dr 54006 == Cr Input GST +
  Cr 23003; bill `itc_reversed`; audit emitted; idempotent on re-call.
- `test_itc_reclaim_restores_credit` — after paid, reclaim Dr Input GST / Cr 14004, balanced; `itc_reclaimed`.
- `test_itc_reclaim_requires_paid_bill` — precondition guard.
- `test_itc_interest_computation` — pure `_compute_itc_interest` value check.

## Verification (performed)

1. `pytest tests/test_business_phase2.py -q` — all green (34 in file; 7 new).
2. `node --check frontend/mitrabooks-erp/app.js` — clean.
3. Real-stack E2E (live Mongo + Postgres ledger + settlement + trial balance): full cycle —
   back-dated bill → flagged with interest → reverse → settlement net payable rose by ₹180 →
   trial balance balanced → mark paid → reclaim → settlement back to baseline → still balanced.
   **13/13 checks passed.**

## Out of scope (parked)

- Formal GSTR-3B / GSTR-1 return documents — here we only tag rows with the 4(B)(2)/4(D)(1) references.
- Auto-running the scanner on a schedule — preview is on-demand this iteration.
- Settlement engine clamps a month's *negative* net ITC to zero (pre-existing); the reversal's
  cash effect only shows when the month has output or fresh ITC to absorb it. Worth revisiting
  alongside the GSTR-3B work.
