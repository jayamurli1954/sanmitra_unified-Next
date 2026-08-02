# LegalMitra Architecture Specification

**Document type:** Architecture / implementation specification  
**Product:** LegalMitra  
**Status:** Companion to the product PRD  
**Version:** 1.0  
**Date:** 2026-07-31  
**Workspace:** `D:\sanmitra_unified-Next`

This document answers **how** LegalMitra is implemented in the SanMitra unified codebase.  
Product **what / why / when** lives in [`docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md`](../prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md).

Do not treat this file as a substitute for the PRD. If product intent and this spec conflict, stop and resolve explicitly with the platform owner.

---

## 1. Related controls

| Artifact | Role |
| --- | --- |
| `docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md` | Product contract and stage gates |
| `D:\Download\LegalMitra_Vision_Implementation_Blueprint.docx` | Working vision (July 2026) |
| `docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md` | Platform scope; LegalMitra separation; Claude gating |
| `docs/architecture/LEGALMITRA_RAG_RESPONSE_CONTRACT.md` | Research response field contract |
| `docs/architecture/LEGALMITRA_STAGE2_1_QUALITY_GATE_AND_CITATION_AUDIT.md` | Planned Stage 2.1 quality gate + citation audit (patterns only) |
| `docs/architecture/LEGALMITRA_TEMPLATE_ENGINE.md` | Launch-grade template rules |
| `docs/architecture/LEGALMITRA_BLOG_EDITORIAL_STANDARD.md` | Insights editorial rules |
| `docs/architecture/MODULE_REGISTRY.md` | Modules `legal`, `rag`, `compliance`, `legal_ai` |
| `docs/operations/STAGED_E2E_PLAN.md` | Stage 1 LegalMitra baseline |
| `AGENTS.md` | Tenant, legal, E2E, and preflight guardrails |

---

## 2. Current code surfaces

| Layer | Location |
| --- | --- |
| Frontend (static HTML/JS) | `frontend/legalmitra/` |
| Canonical legal module | `app/modules/legal/` |
| Primary product APIs (compat) | `app/modules/legal_compat/` |
| RAG / corpus | `app/modules/rag/` |
| Hybrid research assembly | `app/modules/legal_compat/service.py` → `build_hybrid_legal_response` |
| Pricing / fair use | `app/core/billing/pricing.py` (`LEGALMITRA_PRICING`) |

LegalMitra remains a **separate deployable frontend** from MitraBooks Unified ERP.

---

## 3. Module registry

| module_key | Notes |
| --- | --- |
| `legal` | Core LegalMitra workflows |
| `rag` | Knowledge retrieval |
| `compliance` | Deadlines / tracker (must become real in Stage 3) |
| `legal_ai` | Provider AI; default **off** |

Do not add new module keys (`legal_practice`, `tax_intelligence`, etc.) without explicit platform-owner approval and `MODULE_REGISTRY.md` update. Prefer features under existing modules until then.

App key: `legalmitra`. Organization type: `LEGAL`. Persona overlays are profile metadata, not a substitute for module/RBAC checks.

---

## 4. Data ownership

| Store | Ownership |
| --- | --- |
| MongoDB | Clients, matters, drafts, chat history, uploads metadata, audit, domain records |
| Vector store | Embeddings for retrieval |
| BM25 / keyword index | Exact statutory and citation lookup at scale |
| PostgreSQL | Accounting source of truth **only** if/when practice fees post through MitraBooks accounting service |

Never mutate account balances outside the accounting service. Never trust `tenant_id` from request body for protected routes.

---

## 5. Recommended tech stack (Stage 2 decisions)

Aligned to the Vision & Implementation Blueprint; finalize before irreversible schema work (use migration-safety skill).

| Layer | Options |
| --- | --- |
| Backend | Existing FastAPI modular monolith |
| Vectors | PostgreSQL + pgvector, or Qdrant |
| Keyword / BM25 | OpenSearch or Elasticsearch |
| Embeddings | BGE-large or jina-embeddings-v3 (avoid single-vendor lock-in) |
| Rerank | BGE reranker or Cohere Rerank |
| Orchestration (Stage 5) | LangGraph or LlamaIndex |
| Evaluation | RAGAS or DeepEval — citation accuracy and refusal rate from Stage 2 day one |

Near-term: improve the existing hybrid path in `rag/service.py` + `legal_compat` rather than a greenfield rewrite. Shared SanMitra AI Brain across products is **Stage 6**, not Stage 2.

---

## 6. Research pipeline (implementation shape)

```text
Query
  → query understanding / jurisdiction check
  → hybrid retrieval (lexical + vector + metadata + citation lookup)
  → rerank
  → generation only from trusted chunks (or refuse)
  → response contract fields + audit/metrics
```

Enforce `LEGALMITRA_RAG_RESPONSE_CONTRACT.md` end-to-end (API + UI).  
Answer feedback is wired to `POST /api/v1/legalmitra/answer-feedback` (summary for admins).  
First corpus slice: GST + Income Tax; prove on GST refund / Section 54 and IT Section 139 families.  
Authorized Stage 2 offline slices + seed text live under `data/legal_seed/` and `offline_fallbacks.py`.  
Statute PDF ingest (read-only source `D:\sanmitra-backend\data\legal_acts`) is documented in
`docs/operations/LEGALMITRA_STAGE2_STATUTE_INGEST.md`.

---

## 7. Agent layer (later)

Stage 5 target specialists (adapters on FastAPI services, not a separate platform):

- Legal Research Agent  
- Tax / Compliance Agent  
- Drafting Agent  
- Document Agent  
- Matter Agent  
- Calendar / Alerts Agent  

Orchestrator classifies intent, routes, assembles response with citations. Human sign-off required before file/send.

---

## 8. Validation commands

Before commit/push of LegalMitra changes:

```bash
python scripts/preflight.py
```

When `frontend/**` changes:

```bash
python scripts/preflight.py --frontend
```

Add or extend tests for tenant isolation, citation/refusal behavior, and review gates for the risk area changed. Keep Stage 1 LegalMitra baseline green.

---

## 9. Stage mapping to engineering workstreams

| PRD stage | Primary engineering focus |
| --- | --- |
| Now | Stabilize live research/templates; label stubs; feedback endpoint |
| 2 | RAG contract, GST/IT corpus + chunking, rerank, eval harness, launch templates |
| 3 | Mongo Client/Matter APIs; replace tracker localStorage; matter briefs. Spec: [`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md) |
| 4 | Morning Brief + deadline/compliance alerts from real tenant data |
| 5 | Orchestrator + agents + knowledge-graph MVP |
| 6 | Shared SanMitra services; optional MitraBooks fee posting |

---

## 10. Document control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-07-31 | Split from PRD v2.0 so product requirements stay library-agnostic |
| 1.1 | 2026-08-02 | Linked Stage 3 Matter & Client Intelligence implementation spec |
