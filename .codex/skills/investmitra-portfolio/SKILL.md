---
name: investmitra-portfolio
description: InvestMitra portfolio and investment safety workflow. Use when editing holdings, transactions, asset classes, P&L, XIRR, CAGR, valuation, goals, risk profiling, screeners, research integrations, broker/Kite context, FinceptTerminal integration, market data, tax lots, capital gains, or investment analytics.
---

# InvestMitra Portfolio

## Rules

- Never place, modify, cancel, or automate live trades from SanMitra test/development workflows.
- Do not expose order execution tools in UI or backend adapters.
- Do not call broker APIs directly from frontend code.
- Never log broker credentials, request tokens, access tokens, holdings exports, or personal financial data.
- Treat investment recommendations as research/education unless a licensed advisory workflow exists.
- Do not hard-code buy/sell signals for specific instruments.
- Keep tenant/user authorization explicit for every portfolio or research request.
- Use precision-safe numeric types for money, quantities, NAV, prices, fees, taxes, rates, and returns.
- Show source and timestamp for market/research data where available.

## Precision

- Prices, NAV, quantities, rates, and allocation percentages need higher precision than simple currency display.
- Transaction amounts, fees, and taxes should use fixed-precision currency values.
- Compute display rounding separately from stored precision.

## Data Expectations

Investment accounts should usually include:

- tenant/user/family context
- account or portfolio id
- account/institution type
- linked goals where applicable
- currency
- status and audit metadata

Portfolio transactions should usually include:

- tenant/user/family context
- account or portfolio id
- instrument id and asset class
- transaction type
- trade date and settlement date
- quantity, price, gross amount, fees, taxes, net amount, currency
- data source or manual override metadata
- external reference id where imported
- confirmation state

## Calculation Checklist

- Distinguish realized gains, unrealized gains, income, fees, taxes, and cash flows.
- Use XIRR for irregular cash flows and CAGR for point-to-point lump-sum comparisons.
- Make P&L and XIRR reproducible from source transactions/holdings.
- Track capital gains by holding period and asset class.
- Track manual price overrides with actor, timestamp, source, and reason.
- Mark stale prices when older than configured threshold.
- Preserve risk profile, horizon, goal, and suitability separately from holdings.

## Integration Boundaries

- InvestMitra personal finance data must not flow into business books automatically.
- Capital gains or tax exports must be user-initiated and audited.
- No direct writes to MitraBooks ledger tables from InvestMitra code.

## Completion Checklist

- Confirm no trade execution path was introduced.
- Confirm tokens and personal financial data are not logged.
- Confirm portfolio calculations use precision-safe values.
- Confirm recommendations are informational/rule-based unless a licensed advisory workflow exists.
- Confirm data source/timestamp is visible for research output.
- Add tests for tenant isolation and calculation edge cases where practical.
