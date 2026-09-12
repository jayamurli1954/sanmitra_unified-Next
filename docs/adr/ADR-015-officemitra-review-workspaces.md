# ADR-015: OfficeMitra Review workspaces (no new Mitra brands)

**Status:** Accepted  
**Date:** 2026-09-12  
**Accepted:** 2026-09-12  
**Product scope:** OfficeMitra AI — Review, Working papers, Review notes  
**Depends on:** [ADR-014](ADR-014-officemitra-ca-analysis-pack.md), [ADR-002](ADR-002-officemitra-connectors-only.md), [ADR-006](ADR-006-ai-providers-replaceable.md), [ADR-007](ADR-007-officemitra-modular-deployment.md), [ADR-012](ADR-012-officemitra-policy-engine.md)  
**Does not supersede:** [ADR-001](ADR-001-mitrabooks-transactional-core.md), [ADR-003](ADR-003-no-cross-product-db-access.md), [ADR-014](ADR-014-officemitra-ca-analysis-pack.md), LegalMitra as a separate product, accounting doctrine in `AGENTS.md` §10

PRD: [docs/prd/OFFICEMITRA_REVIEW_WORKSPACES.md](../prd/OFFICEMITRA_REVIEW_WORKSPACES.md)

## Context

CA review (scan, schedules, notes) is a real next slice on top of OfficeMitra MIS and the internal SSDV engine. Expanding that idea into ten *Mitra sub-products (ClientMitra, ComplianceMitra, ReviewMitra, and so on) would fork MitraBooks CA practice, LegalMitra’s CA persona, and OfficeMitra MIS, and would contradict the rule that OfficeMitra is not the SanMitra operating system.

Platform owner decision (2026-09-12): no additional Mitra brands. Build three OfficeMitra workspaces now. Other practice capabilities may become **packages under OfficeMitra later**, never separate product names.

## Decision

1. **Brands stay:** GruhaMitra, MandirMitra, MitraBooks, LegalMitra, OfficeMitra. InvestMitra remains out of unified scope. Do not add new Mitra product names.

2. **Build now** under module `office_ai`, default-off flags:
   - `office_ai.review`
   - `office_ai.review.working_papers`
   - `office_ai.review.notes`

3. **Later packages** (clients/documents, compliance, knowledge, notices, advisory, team, analytics) may be added as OfficeMitra feature flags only after this slice smokes. They must not ship as new brands. Knowledge and notices stay LegalMitra unless a later ADR explicitly composes them into OfficeMitra.

4. **SSDV** is an internal in-process engine. No end-user CLI or SSDV Streamlit in SanMitra.

5. **Review ingest** writes OfficeMitra-owned Mongo / a review sandbox. It must not post into the live MitraBooks PostgreSQL ledger.

6. **Review risk score** is a separate metric from ADR-014 `data_quality_score`.

7. **Review notes** reuse OfficeMitra tasks and ADR-012 policy. Do not create a third task system.

## Consequences

- Implementation follows [OFFICEMITRA_REVIEW_WORKSPACES.md](../prd/OFFICEMITRA_REVIEW_WORKSPACES.md).
- Agents must not scaffold ClientMitra / PracticeOS / extra Mitra apps.
- ADR-014 MIS remains the import/fact/export backbone; Review adds engagement, findings, schedules, and notes on top.
- Production enablement stays flag-gated and demo-tenant smoked before any live CA tenant.
