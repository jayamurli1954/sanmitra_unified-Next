# Accounting Doctrine

## Purpose

This document defines the accounting rules that every MitraBooks accounting implementation must follow. These rules are mandatory for all SanMitra modules that post financial transactions.

## Double-Entry Accounting

The double-entry accounting system is a bookkeeping method where every financial transaction affects at least two accounts through equal and opposing debit and credit entries.

The core accounting equation must always hold:

```text
Assets = Liabilities + Equity
```

## Modern Account Types

| Account type | Meaning | Debits | Credits |
| --- | --- | --- | --- |
| Assets | Economic resources owned, such as cash, bank, receivables, inventory, buildings | Increase | Decrease |
| Liabilities | Obligations owed to outsiders, such as loans and accounts payable | Decrease | Increase |
| Equity | Owner/trust residual interest after deducting liabilities, such as retained earnings or capital | Decrease | Increase |
| Revenue | Income generated from operations, such as sales, service income, donations, fees | Decrease | Increase |
| Expenses | Costs incurred to operate or generate revenue, such as rent, salaries, utilities | Increase | Decrease |

## Traditional Golden Rules

| Traditional account type | Meaning | Golden rule |
| --- | --- | --- |
| Real accounts | Tangible or intangible property and possessions, such as cash, buildings, machinery, patents | Debit what comes in, credit what goes out |
| Personal accounts | Individuals, companies, legal entities, debtors, creditors, banks, capital accounts | Debit the receiver, credit the giver |
| Nominal accounts | Income, gains, expenses, and losses, such as salary expense, rent, interest earned, sales | Debit all expenses and losses, credit all incomes and gains |

## Mandatory Coding Constraints

### 1. Atomicity

Every accounting posting must be wrapped in one database transaction. Either all debit and credit lines commit together, or none commit.

### 2. Balance Validation

Before committing any journal entry:

```text
sum(debits) - sum(credits) = 0
```

If the equation is not exactly zero, reject the posting.

### 3. Immutable Ledgers

Posted transactions must be append-only.

Do not:

- Update posted journal entries.
- Delete posted journal entries.
- Mutate balances directly.

Corrections must be made through:

- Reversal entries.
- Adjustment entries.
- Linked correcting journal entries.

### 4. High-Precision Amounts

Never use binary floating-point types for money.

Use one of:

- Integer minor units, such as paise/cents.
- Fixed-precision decimal type.
- Database numeric/decimal with explicit scale and precision.

### 5. Auditability

Every posting must retain:

- `tenant_id`
- source module
- source document/reference
- actor/user
- timestamp
- posting status
- reversal link where applicable
- idempotency key where applicable

## Cross-Module Rule

GruhaMitra, MandirMitra, MitraBooks business, and LegalMitra billing must not implement their own accounting engines. They must call the shared MitraBooks accounting service for financial postings.

InvestMitra is excluded from SanMitra unified backend and deployment scope.
