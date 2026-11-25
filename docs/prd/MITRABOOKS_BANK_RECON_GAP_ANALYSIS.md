# MitraBooks Bank Reconciliation — Gap Analysis vs TallyPrime and Zoho Books

Date: 2026-11-25
Scope: `app/modules/business/bank_recon.py`, `app/modules/business/routes/bank_recon_routes.py`,
`frontend/mitrabooks-erp/modules/workspaces/bank-recon.js`.

## Method and boundaries

This is a clean-room comparison. It uses only the publicly documented behaviour of
TallyPrime (TallyHelp) and Zoho Books (Zoho Books Help, India edition). No vendor
software was decompiled or inspected, and nothing here copies vendor code, screens
or text. The vendor columns describe documented features as of this writing.
Vendor features change between releases, so re-check the vendor help pages before
using a row to make a commitment to a customer.

MitraBooks guardrails that every gap fix must keep (from the module docstring and
`docs/operations/MITRABOOKS_BANK_FEED_POLICY.md`):

- Matching is metadata only and never posts to the GL.
- Suggestions are never applied automatically. The accountant confirms each match
  (maker-checker).
- Bank-only lines post only through the typed-voucher review path.
- All data is scoped by tenant, app key and accounting entity.

## Current MitraBooks capability (baseline)

| Area | What exists |
|---|---|
| Statement import | CSV only. Tolerant header aliases for Indian banks: separate Dr/Cr columns, single amount with a Dr/Cr indicator, or a signed amount. Eight date formats. Re-uploads are deduplicated by fingerprint. Every import is audit-logged. |
| Matching engine | `suggest_matches`: **one-to-one only.** Amount and direction must agree exactly, dates within ±7 days. A reference hit raises the confidence. Greedy assignment, closest date first. |
| Confirm / undo | One statement line ↔ one book line per match (`create_bank_recon_match`). Soft reverse. |
| Bank-only lines | Post a journal voucher against a chosen offset account, through the approval path. |
| BRS | Balance as per books, balance as per bank, expected balance, difference. Uncleared cheques, deposits in transit, and bank-only debits and credits. |
| UI | Account picker, CSV upload, suggestions table (Match), bank-only table (Post voucher), book-only table, matched table (Unmatch). |

## Gap matrix

Legend: ✅ present · ◐ partial · ❌ missing.
Priority: **P1** = needed for real-world Indian SME reconciliation; **P2** = significant time saver; **P3** = nice to have.

| # | Capability | TallyPrime (documented) | Zoho Books (documented) | MitraBooks today | Gap | Priority |
|---|---|---|---|---|---|---|
| 1 | **One-to-many / many-to-one matching** (one bank line ↔ several vouchers, or the reverse) | Reconciliation works per voucher, with a bank date set on each voucher. A combined deposit is handled by giving each voucher the same bank date. There is no explicit grouped-match object. | "Match" lets you select several transactions against one statement line. Totals must agree, or the difference can be recorded as a bank charge or adjustment. | ❌ Strictly 1:1, both in suggestions and in confirm. | Engine plus confirm endpoint plus UI. **Being built first (see the section below).** | P1 |
| 2 | Manual matching (pick any book line for a statement line) | ✅ The user enters the bank date against any voucher. | ✅ Search and select transactions manually. | ❌ The user can only confirm a suggestion. If no suggestion appears, the line cannot be matched. | Manual-pick UI plus API (the API already accepts any pair). | P1 |
| 3 | Match with a difference (bank charges, TDS, rounding) | Record the charges as a separate voucher. | ✅ An "Add bank charges / adjustment" step during matching posts the difference. | ❌ Exact amounts only. | Tolerance suggestion plus "post the difference" voucher through the approval path. | P1 |
| 4 | Rules for recurring narrations (for example "a description containing X goes to ledger Y") | ◐ Party/ledger mapping during bank-statement import in newer releases. | ✅ Bank rules: criteria on description, amount, reference or payee, with actions such as categorise, contact or account. | ❌ | Rules engine that *pre-fills* the offset account and voucher draft. It must still require confirmation. | P2 |
| 5 | Auto-reconciliation from an imported statement | ✅ Import a bank statement and the auto-reconciliation feature matches on instrument number, amount and date. | ✅ Auto-match with "best match" and "possible matches". | ◐ Suggestions exist; the user must confirm each one, which is by design. | Add a "confirm all reference-confidence suggestions" bulk action that keeps maker-checker. | P2 |
| 6 | Statement formats | Excel and a set of bank-specific formats. Connected banking with partner banks. | CSV, TSV, OFX, QIF, CAMT.053 and PDF import. Direct bank feeds. | ◐ CSV only. | Excel (.xlsx) and OFX/CAMT parsers that feed the same statement-line model. Bank feeds stay deferred per the bank-feed policy. | P2 |
| 7 | Instrument / cheque tracking (cheque number and date on the voucher) | ✅ Instrument number, instrument date and bank date on each voucher. Cheque register, post-dated cheques. | ✅ Cheque number and reference fields. | ◐ Reference is free text only. Matching uses a substring of it. | Structured `instrument_no` on bank vouchers, plus normalised UPI/NEFT/IMPS/UTR reference extraction from narrations. | P2 |
| 8 | Reconciliation by statement period with a closing balance (lock the period once it is reconciled) | ◐ BRS as of a date. Opening BRS for balances brought forward. | ✅ "Reconcile account": start/end date and closing balance. Undo reconciliation. | ◐ As-of date only. The closing balance comes from the CSV's last balance column. No period lock. | A reconciliation session record (period, statement closing balance, signed off by, locked). Undo creates an audit event. | P2 |
| 9 | Opening BRS (uncleared items carried in from before MitraBooks) | ✅ Opening BRS. | ◐ Through the opening balance plus uncategorised lines. | ❌ | Allow opening uncleared items to be entered against the opening balance. | P2 |
| 10 | Exclude / ignore a statement line (duplicates, already handled elsewhere) | ◐ | ✅ Exclude and restore. | ❌ The line stays "in bank, not in books" forever. | Soft-exclude with a reason, audited. It must still appear in the BRS appendix. | P3 |
| 11 | Split one statement line across several ledgers when posting | Through a multi-ledger voucher. | ✅ Split transaction. | ❌ The voucher has one offset account. | A multi-line voucher from a statement line. | P3 |
| 12 | Posting a bank-only line also reconciles it | ✅ (the voucher carries a bank date) | ✅ (a categorised line is reconciled) | ◐ The voucher posts, but the line is **not** auto-matched. It reappears as a suggestion against its own new journal line. | After the voucher is posted, create the match through the normal metadata path. | P2 |
| 13 | BRS print/export | ✅ | ✅ | ◐ JSON plus on-screen view. | PDF/Excel export through `report_export.py`. | P3 |
| 14 | Concurrency safety on confirm | n/a (desktop) | n/a | ◐ The "already matched" check and the insert are not atomic. Two users could double-match the same line. | A unique partial index on active `statement_line_id`/`line_id`, or a conditional upsert. | P2 |

## Recommended build order

1. **One-to-many / many-to-one matching** (#1), the subject of this change.
2. Manual matching UI (#2). It reuses the group-match endpoint built here. The UI in this change already lets the user tick lines and press "Match selected".
3. Match with a difference (#3), as a follow-on to group matching.
4. Auto-match after a voucher is posted from a bank-only line (#12), plus atomic confirm (#14).
5. Bank rules (#4) and reference normalisation (#7).
6. Statement periods and locks (#8), and opening BRS (#9).
7. Additional formats (#6), exclude (#10), split (#11), export (#13).

## Design: one-to-many matching (implemented with this document)

**Use cases**

- One bank deposit covers several customer receipts (a cash or cheque deposit slip, or a UPI/POS settlement batch). This is 1 statement line ↔ N book lines.
- One bank debit covers several payment vouchers (a bulk NEFT, or a salary batch posted employee by employee). This is also 1 statement line ↔ N book lines.
- One book payment is split by the bank into several debits (for example IMPS limits). This is N statement lines ↔ 1 book line.

Many-to-many (N ↔ M) is intentionally out of scope. Splitting it into 1:N groups keeps the audit trail readable.

**Storage.** A group match writes one document per pair into the existing
`business_bank_recon_matches` collection. All of them share a `match_group_id` and
carry a `group_type` (`one_to_many` or `many_to_one`), the `group_size` and the
`group_amount`. Every row keeps scalar `statement_line_id` and `line_id` fields, so
existing readers need no change: the BRS assembler, data-health and indexes all
build sets from those fields.
Each row's `amount` is its own share. In a 1:N group that is the book line's amount;
in an N:1 group it is the statement line's amount. So summing `amount` over the
active rows never double counts.

**Rules (all enforced server-side)**

- At least one side has exactly one line. The other side has at least two lines and at most `GROUP_MATCH_MAX_LINES` (10).
- No duplicate ids. Every line must exist in scope on this bank account and must not already be in an active match.
- Every line must be on the same side (all deposits ↔ book debits, or all withdrawals ↔ book credits).
- Totals must agree **exactly** (to the paisa). Tolerance is gap #3, not part of this change.
- Reversing any row of a group reverses the whole group. This prevents a half-matched statement line.

**Suggestions.** `suggest_group_matches` runs after the 1:1 pass, on whatever is
still unmatched and unsuggested. For each single line it looks for a subset of
opposite lines on the same side, within the date window, whose amounts sum
exactly to it.

- The search is bounded: at most 12 nearest-dated candidates, subsets of up to 4 lines, and a cap on search steps.
- Fewer lines and closer dates win.
- When more than one distinct subset fits, the suggestion is labelled `ambiguous` so the accountant looks closely.
- Lines are never reused across suggestions.
- Suggestions are returned in the reconciliation payload as `group_suggestions` and are never applied automatically.

**API.** `POST /api/v1/business/bank-recon/match-group` with the body
`{account_id, statement_line_ids: [...], line_ids: [...]}`. It returns the group
id and its rows. The existing `POST /bank-recon/match/{match_id}/reverse` reverses
the whole group.
