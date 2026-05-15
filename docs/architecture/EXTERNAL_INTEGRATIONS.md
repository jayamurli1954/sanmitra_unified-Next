# External Integration Plan

## Purpose

This document captures planned integrations discussed for InvestMitra and LegalMitra so they are not lost during the unified-platform refactor.

These are strategic integrations, not first-PR implementation tasks.

## Summary

| Integration | Product | Purpose | Execution Boundary |
| --- | --- | --- | --- |
| FinceptTerminal | InvestMitra | Investment research, analytics, economic data, research reports | Research only, no trading |
| Zerodha Kite MCP | InvestMitra | User-authorized market/portfolio context for research | Read-only, no order tools |
| Claude for Legal | LegalMitra | Legal workflow assistant, drafting/review/research support | Human review, source attribution, confidentiality |

## Phase 0: Documentation and Risk Review

Before coding:

- Confirm licensing and commercial-use constraints.
- Confirm data retention and privacy rules.
- Confirm whether integrations are tenant-level, user-level, or both.
- Define allowed and forbidden tool methods.
- Define audit logging requirements.
- Define UI disclaimers and human-review workflow.

## Phase 1: Adapter Interfaces

Create internal adapter boundaries without provider-specific UI assumptions.

Suggested shape:

```text
app/integrations/
  investment_research/
    base.py
    fincept_terminal.py
  broker_research/
    base.py
    zerodha_kite_mcp.py
  legal_ai/
    base.py
    claude_for_legal.py
```

No external tool should be called directly from frontend code.

## Phase 2: Read-Only Proofs of Concept

### FinceptTerminal POC

- Pull or ingest research outputs.
- Generate a sample research summary.
- Validate licensing and attribution.
- Avoid dependency on desktop-only UI if backend integration is required.

### Zerodha Kite MCP POC

- Authenticate in a user-controlled way.
- Read instruments, holdings, quotes, or historical data where allowed.
- Explicitly disable or omit order placement tools.
- Audit every access.

### Claude for Legal POC

- Use a controlled legal document/research workflow.
- Preserve source citations.
- Require human review before output is finalized.
- Validate tenant isolation and confidentiality.

## Phase 3: Product Integration

### InvestMitra

Add research screens:

- Research dashboard.
- Watchlist enrichment.
- Portfolio-aware research notes.
- Holding risk/concentration.
- Fundamental and macro summaries.

No trading workflow should be exposed.

### LegalMitra

Add legal assistant screens:

- Document review.
- Drafting support.
- Case summarization.
- Compliance checklist assistance.
- Citation verification workflow.

## Phase 4: Tenant/Plan Enablement

Enable integrations only via module flags:

- `investment_research`
- `broker_research`
- `legal_ai`

Default should be off until each integration passes security, licensing, and workflow review.

## Non-Negotiable Guardrails

### InvestMitra

- No buy orders.
- No sell orders.
- No modify/cancel order operations.
- No automated trading.
- No financial advice phrased as guaranteed outcome.
- Show data source and timestamp.

### LegalMitra

- No uncited legal research answer.
- No hallucinated citations.
- No final legal advice without lawyer/user review.
- Preserve client confidentiality.
- Log access according to tenant policy.
