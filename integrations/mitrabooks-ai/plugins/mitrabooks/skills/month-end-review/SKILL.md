---
name: month-end-review
description: Review a MitraBooks company's books for a month before closing it - trial balance, data-health issues, unreconciled bank items, unallocated payments, aging, pending approvals - and produce a prioritised fix list. Use when the user asks for a month-end close check, book review, "are my books ready", or a pre-closing health check on MitraBooks.
---

# MitraBooks month-end review

You are reviewing the books, not changing them. Every MitraBooks tool is read-only.
Report what you find; the user fixes entries in MitraBooks.

## Inputs
- The month to review (YYYY-MM). If not given, ask; default to the previous calendar month.
- Optional: accounting_entity_id if the user has more than one set of books.

Work out the month's first and last dates. Remember the Indian financial year runs April-March.

## Steps

1. **Does it balance?** `get_trial_balance(as_of=<month end>)`. If `balanced` is false, stop
   and report the difference first - nothing else matters until that is fixed.
2. **Data health.** `get_data_health(as_of=<month end>)`. List every failing rule with its
   evidence (document numbers, counts, amounts).
3. **Drafts and approvals.** `list_pending_approvals()`. Anything dated in the month that is
   still draft or pending approval is missing from the books. (Needs a tenant admin; if the
   tool says not permitted, say so and move on.)
4. **Bank.** `list_accounts()` and pick accounts flagged cash/bank. For each bank account,
   `get_bank_reconciliation(account_id, as_of=<month end>)`. Report the difference between
   book and statement balance and the unreconciled items on each side, oldest first.
5. **Receivables and payables.**
   - `list_unallocated_payments(kind="receivable")` and `(kind="payable")` - receipts and
     payments not matched to invoices or bills.
   - `get_aging_report(kind="receivable", as_of=<month end>)` and the payable equivalent.
     Call out the 90+ bucket and the largest overdue parties.
6. **Results sanity check.** `get_profit_and_loss(from_date=<month start>, to_date=<month end>)`.
   Compare with the previous month (call it again for that month). Flag lines that moved
   sharply or changed sign, and expense heads that are zero this month but were not last month
   (possible missed accruals or bills).

## Output

A short report with:
- **Status line:** Ready to close / Close with caveats / Not ready.
- **Blocking issues** (trial balance difference, unposted documents in the month, unreconciled
  bank differences) - each with the document or amount and what to do in MitraBooks.
- **Should fix** (unallocated payments, data-health warnings, aged receivables).
- **For information** (P&L movements worth a look).

Quote amounts in INR exactly as the tools return them. Do not invent figures, rates or due
dates; if something is needed that no tool returns, say so.
