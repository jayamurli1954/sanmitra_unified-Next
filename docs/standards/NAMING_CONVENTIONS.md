# Naming Conventions

## Product Names

Use:

- GruhaMitra
- MandirMitra
- MitraBooks
- LegalMitra
- InvestMitra

InvestMitra remains a valid product name, but it is excluded from SanMitra unified backend and deployment scope. Use InvestMitra naming only for archived references or separately authorized personal-use InvestMitra work.

Do not use:

- GharMitra
- GrihaMitra
- Gruha Mitra
- Mandir Mitra
- Mitra Books

## App Keys

Use lowercase app keys for API context:

- `gruhamitra`
- `mandirmitra`
- `mitrabooks`
- `legalmitra`
- `investmitra`

`investmitra` is reserved for separate personal-use InvestMitra work and must not be added to unified backend routing or deployment without an explicit scope reversal.

## Organization Types

Use uppercase enum values:

- `HOUSING`
- `TEMPLE`
- `BUSINESS`
- `PROFESSIONAL`
- `LEGAL`
- `INVESTMENT`

`INVESTMENT` is reserved outside unified SanMitra backend scope.

## Module Keys

Use lowercase snake case:

- `housing`
- `temple`
- `business`
- `professional`
- `accounting`
- `gst`
- `inventory`
- `legal`
- `rag`
- `investment`
- `portfolio`
- `audit`

`investment` and `portfolio` are reserved outside unified SanMitra backend scope.

## Source Systems

Use these values for COA mapping and legacy import context:

- `gruha_mitra`
- `mandir_mitra`
- `mitra_books`
- `legal_mitra`
- `invest_mitra`

If existing code already uses `ghar_mitra`, keep compatibility during migration but normalize new docs and new code to `gruha_mitra`.
