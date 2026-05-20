---
name: mitrabooks-erp
description: MitraBooks Unified ERP workflow for business accounting, parties, vouchers, invoices, purchases, inventory, GST/tax, TDS, reports, payments, receivables, payables, dashboards, compatibility APIs, and ERP integrations for MandirMitra and GruhaMitra. Use when changing MitraBooks ERP backend, frontend, financial documents, or ERP route contracts.
---

# MitraBooks ERP

## Scope

MitraBooks is the shared accounting/business engine and the target ERP shell for:

- business accounting workflows
- MandirMitra temple/trust donation and seva accounting
- GruhaMitra housing maintenance and society accounting

LegalMitra and InvestMitra stay separate product experiences unless explicitly decided otherwise.

## Document Impact

Common accounting impacts:

- Sales invoice: debit accounts receivable, credit revenue and tax payable.
- Purchase bill: debit expense/asset and eligible tax input, credit accounts payable.
- Payment received: debit bank/cash, credit accounts receivable.
- Payment made: debit accounts payable, credit bank/cash.
- Credit note: reverse or reduce sales revenue/tax/receivable as appropriate.
- Debit note: reverse or reduce purchase expense/asset/tax/payable as appropriate.
- Journal entry: use explicitly provided debit/credit lines.

## Document Lifecycle

Typical statuses:

- `draft`
- `submitted` or `issued`
- `approved` where tenant workflow requires approval
- `posted`
- `paid` or `partially_paid`
- `cancelled` or `voided`
- `reversed`

Rules:

- Only draft/pre-posted documents may be edited directly.
- Posted financial documents must not be physically deleted.
- Corrections after posting use credit/debit notes, reversal, or adjustment entries.

## GST, TDS, And Inventory

- GST rates must be configurable by jurisdiction and effective date.
- GST components should be separable for reporting: CGST, SGST, IGST, CESS.
- HSN/SAC should be captured where needed for GST reporting.
- TDS sections/rates must be configurable by vendor and transaction type.
- TDS deductions post to a TDS payable liability account.
- Inventory valuation method must be explicit: FIFO, weighted average, standard cost, or specific identification.
- Stock adjustments must be audited and posted through accounting.

## Reports And Chart Of Accounts

- Financial reports must derive from posted ledger entries.
- Draft/unposted records must not affect financial totals unless an explicit `include_drafts` flag and warning exist.
- Comparative reports should use posting date unless tenant configuration says otherwise.
- Every tenant owns its own chart of accounts.
- System accounts such as AR, AP, tax payable, TDS payable, bank/cash, and rounding difference must be protected from deletion.

## Integration Contract

Other domains must post through the shared accounting service and provide:

- source module
- source document id and type
- transaction/posting date
- tenant context
- reference number
- debit/credit lines
- currency
- actor and idempotency key where applicable

## Completion Checklist

- Confirm document status lifecycle.
- Confirm accounting integration uses service layer.
- Confirm idempotency and rollback/compensation for financial POSTs.
- Confirm tax logic is configurable.
- Confirm reports use validated ledger/document sources.
- Confirm frontend route usage still matches backend route contracts.
- Add accounting, tenant, and route-contract tests where practical.
