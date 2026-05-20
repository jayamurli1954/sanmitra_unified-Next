---
name: accounting-doctrine
description: SanMitra accounting integrity workflow for MitraBooks and financial integrations. Use when editing journals, ledger lines, accounts, invoices, receipts, payments, expenses, donations, seva collections, maintenance collections, reports, reconciliation, GST, TDS, tax records, money fields, portfolio values, or any workflow that posts or reverses financial transactions.
---

# Accounting Doctrine

## Non-Negotiables

- Use double-entry accounting: total debits must equal total credits.
- Do not use binary floating-point types for money, units, NAV, rates, or prices.
- Use integer minor units or fixed-precision decimals with explicit currency where relevant.
- Do not mutate balances directly; derive them from posted journal/ledger entries.
- Posted entries are immutable. Correct by reversal or adjustment entry.
- Financial posting must be atomic and audited.
- Domain modules must call the shared accounting service instead of writing ledger rows directly.
- Do not use negative debits/credits to represent the opposite side; use the correct debit or credit field.

## Required Posting Shape

Every posting should retain:

- `tenant_id`
- journal or posting reference
- transaction date and posting date
- source module, source document type, and source document id
- human-readable reference number when available
- debit and credit account references
- debit and credit amounts with currency
- actor/user context
- idempotency key for financial POSTs where applicable
- status such as `draft`, `posted`, `reversed`, or `voided`
- audit event or audit metadata
- reversal link when corrected

## Journal Line Expectations

Each ledger line should retain:

- journal/header id
- tenant-scoped account id
- debit amount
- credit amount
- currency code
- description or memo

Exactly one side should be non-zero for normal debit/credit lines.

## Tax And Rounding

- Tax rates must be configurable by jurisdiction and effective date; do not hard-code GST/TDS rates into posting logic.
- GST components such as CGST, SGST, IGST, and CESS should be represented separately when needed for reporting.
- TDS deductions should post to a TDS liability account.
- Rounding strategy must be explicit in the service layer.
- Rounding differences must post to a dedicated rounding difference account, never silently disappear.

## Review Pattern

1. Find all money and quantity fields and confirm precision-safe storage.
2. Find the service boundary that posts accounting entries.
3. Confirm the posting runs in one transaction or has explicit compensation for cross-store workflows.
4. Confirm unbalanced postings fail before persistence.
5. Confirm posted records cannot be edited or deleted in place.
6. Confirm reporting reads from posted/accounting-safe sources.

## Tests

Add or update tests for:

- balanced postings accepted
- unbalanced postings rejected
- duplicate idempotency key behavior
- decimal precision and rounding behavior
- reversal behavior
- accounting failure rollback/compensation for domain records
- tenant isolation on accounts, journals, reports, and source documents
