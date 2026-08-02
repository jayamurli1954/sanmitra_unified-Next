# LegalMitra Professional Intelligence Platform PRD

**Document type:** Product Requirements Document  
**Product:** LegalMitra  
**Status:** Approved for implementation (living document)  
**Version:** 2.0  
**Date:** 2026-07-31  

This PRD is the **engineering contract** for what LegalMitra must do and in what order.  
Vision *why* lives in the LegalMitra Vision & Implementation Blueprint.  
*How* (libraries, services, schemas, repo paths) lives in the companion [Architecture Specification](../architecture/LEGALMITRA_ARCHITECTURE_SPEC.md).

Keep this document product-focused and readable. Prefer updating stages over growing toward a 100-page specification. Target length: enough for one sitting, roughly **30–50 pages** of substance if printed—not a second vision book.

---

## Product North Star

### Mission

Build the most trusted Professional Intelligence Platform for Indian legal, tax, compliance, and governance professionals—so they spend time exercising judgment, not searching for information.

### Target user

Advocates and law firms, Chartered Accountants and tax practitioners, Company Secretaries, corporate legal advisors, and compliance professionals who share the same workday loop—intake → research → draft → review → deliver → track—and need one intelligent workspace that adapts to their role.

### Competitive advantage

Legalit and similar products are the **benchmark** for practice-management breadth and daily stickiness. LegalMitra differentiates on grounded research with citations and refusal, matter/client intelligence, proactive alerts, and multi-persona reach (Advocate / CA / CS / Corporate)—not on matching every competing screen.

### Success definition

LegalMitra succeeds when professionals open it daily because it surfaces what matters, answers with traceable authority or honest refusal, and never pretends AI output is final professional advice—while adoption and trust grow before deep practice-OS breadth.

**Feature filter:** Does this reduce cognitive load without reducing professional judgment or source trust?

---

## 1. Positioning

| Benchmark pattern | LegalMitra response |
| --- | --- |
| Breadth-first practice management + AI features | Intelligence-first platform; practice ops as backbone |
| Many widgets and modules | Persona-adaptive workspace + proactive associate |
| Reactive software | Surfaces risks, deadlines, and amendments unasked |
| Feature-oriented AI buttons | One Professional Brain with specialist capabilities |

LegalMitra is **not** an “AI legal chatbot.” It is a **Professional Intelligence Platform**.

Core philosophy:

1. Knowledge before generation  
2. Trust before speed  
3. Explain everything  
4. AI assists; professionals decide  
5. One workspace  
6. Proactive, not reactive  

---

## 2. Current / Target / Gap

### Current state

LegalMitra is **live** as a separate product experience: research chat with hybrid retrieval and optional provider assist, templates and official forms, plan-based usage limits, marketing Insights, and a compliance tracker UI that is still largely demo/stub.

| Area | Classification |
| --- | --- |
| Auth, tenancy, app context | Implemented |
| Legal research / chat | Partial |
| Optional advanced AI counsel | Partial / production-gated |
| Knowledge corpus quality | Partial |
| Templates / official forms | Partial (launch-grade set incomplete) |
| Document review upload | Partial |
| Case / matter management | Thin / stub |
| Compliance tracker / CRM / fee ledger | Stub |
| Court calendar / cause list / time tracking | Missing |
| Knowledge graph / matter intelligence / agents | Missing |
| Data-backed persona dashboards | Missing |

### Target state

One product shell for Advocate, CA, CS, Corporate Legal (and later light Compliance / business-owner views) with:

- Trusted research (citations, confidence, refusal)  
- Drafting and templates with human review  
- Shared practice operations (clients, matters/engagements, calendar, tasks)  
- Persona intelligence packs  
- Proactive Morning Brief and risk alerts  
- Later: matter intelligence and agentic workflows with human gates  

LegalMitra stays a **separate product experience** from MitraBooks Unified ERP. Practice billing may later post into shared accounting where needed; LegalMitra must not become the accounting engine.

### Gap (build order)

| Priority | Gap |
| --- | --- |
| P0 | Full research safety contract (citations, confidence, refusal, human review) |
| P0 | GST + Income Tax corpus quality + structured legal chunking |
| P0 | Launch-grade templates in primary marketplace |
| P1 | Tenant-backed clients/matters; end fake tracker metrics |
| P1 | Persona-adaptive workspace; deadlines/alerts |
| P1 | Retrieval reranking + AI quality metrics + answer feedback |
| P1 | Production advanced-AI enablement checklist (not silent on) |
| P2 | Document intelligence; Morning Brief (production); practice billing |
| P2–P3 | Knowledge graph; matter intelligence; agentic workflows |

---

## 3. Things We Intentionally Won't Build Yet

Elevate these so scope creep has nowhere to hide:

- Feature-count race with Legalit (benchmark ≠ clone)  
- Merging LegalMitra into the MitraBooks ERP shell  
- Spreading AI/RAG investment across MandirMitra, GruhaMitra, and MitraBooks before LegalMitra Stage 2 is proven  
- Matter intelligence / agentic workflows before meaningful multi-user adoption  
- Autonomous filing to courts, MCA, GST, or Income Tax portals  
- Voice assistant as a product pillar  
- Native mobile apps (responsive web first)  
- International / multi-country law coverage  
- Blockchain or crypto-ledger “legal proof” features  
- OCR for every language and every document type  
- Claiming zero hallucination  
- Presenting AI output as final legal advice or replacing professional responsibility  
- Enabling advanced external AI for production tenants without confidentiality, retention, attribution, human-review, and live-baseline approval  
- InvestMitra / investment research scope  

---

## 4. Personas

Design around the professional workday, not job-title silos. All personas share: intake → research → draft/compute → review → deliver → track.

| Persona | Core daily work | Where intelligence helps most |
| --- | --- | --- |
| Advocate / law firm | Cases, hearings, drafting, research, fees | Precedent research, draft checks, limitation alerts |
| Chartered Accountant | GST/TDS/IT, audits, client queries | Notice interpretation, compliance calendar, statute-backed answers |
| Company Secretary | ROC/MCA, board meetings, registers | Filing deadlines, governance checklists, draft resolutions |
| Corporate legal advisor | Contracts, litigation oversight, policy, risk | Clause risk, playbook deviation, cross-matter patterns |
| Business owner / SMB (later, light) | Basic compliance and contracts | Plain-language guidance, nudges, document review |

Secondary later: Compliance Officer, CFO light view—same shell, fewer privileges.

---

## 5. Capability Map

```text
LegalMitra
├── Knowledge & Research
├── Document Intelligence
├── Practice Operations
├── Compliance & Governance packs
├── Drafting & Templates
├── Finance & Billing (practice-level)
├── Communication & Collaboration
├── Analytics & Observability
└── Professional Intelligence (orchestrated specialists)
```

| Capability | Now | Next meaningful stage |
| --- | --- | --- |
| Knowledge & Research | Partial | Stage 2 |
| Drafting & Templates | Partial | Stage 2 |
| Practice Operations | Stub | Stage 3 |
| Compliance packs | UI stub | Stage 3–4 |
| Document Intelligence | Upload review only | Stage 3–4 |
| Practice Finance | Stub | Stage 4+ |
| Proactive Assistant | Missing | Stage 4 (demo earlier) |
| Agentic workflows | Missing | Stage 5 |
| Shared SanMitra intelligence | Not yet | Stage 6 |

---

## 6. Product Requirements

Use **Must / Should / May**. Traceability IDs are reserved for requirements that must survive audits, safety gates, or stage exits. Everyday backlog items need not be numbered.

### 6.1 Trust, tenancy, and access (Must)

- Protected LegalMitra features resolve tenant, product context, role, and enabled capabilities from trusted context—never from unverified client claims alone.  
- Persona preference (Advocate / CA / CS / Corporate) customizes experience; it must not bypass access control.  
- Advanced external AI remains off by default until the production gate checklist passes.  
- Public/marketing paths must never expose another tenant’s private matters or documents.

### 6.2 Research intelligence (core differentiator)

**Must**

- Every research answer is structured for safety: summary, citations or insufficient-source refusal, confidence, limitations, advisory notice, and human-review required.  
- First production-quality knowledge slice is **GST + Income Tax**, proven on a narrow subdomain (recommended: GST refund / Section 54 family) before broad Bare Act expansion.  
- Retrieval combines exact legal-term search, semantic search, and metadata filters (Act, section, jurisdiction, effective date).  
- Chunking follows legal structure (Act → Chapter → Section → Explanation), not blind fixed windows.  
- Answers must not cite authority that was not retrieved or explicitly authorized.  
- Jurisdiction-dependent questions without jurisdiction refuse and ask for it.  
- Weak evidence triggers refusal—not invented case names, sections, or courts.  
- Users can rate answers; quality signals (citation failures, refusals, low confidence) are measurable from day one of Stage 2.

**Should**

- Rerank near-miss legal concepts before generation.  
- Surface statute version / effective-date awareness in limitations.  
- Early Morning Brief / role dashboard demo for visibility (full production in Stage 4).

**May (later stages)**

- Knowledge graph linking section ↔ notification ↔ circular ↔ judgment.

### 6.3 Drafting and templates

**Must:** Primary marketplace emphasizes a small launch-grade set (consultancy, software development, NDA, employment, website terms/privacy), clause-driven where required, exportable, with human-review disclaimer. AI drafts stay advisory with review state. Official forms stay plan-gated and validated.  

**Should:** Hide or label thin legacy templates until upgraded.

### 6.4 Practice operations

**Must (Stage 3):** Tenant-scoped Clients and Matters/Engagements; replace demo tracker data with real persisted practice data; deadlines/tasks with audit.  

**Should:** Richer case status, parties, jurisdiction, assignment.  

**May:** Cause-list / court sync.

### 6.5 Persona workspace

**Must:** Onboarding captures primary persona; navigation and defaults adapt.  

**Should:** Advocate pack depth first among practice packs; CA (GST/IT calendar, notices), CS (board/ROC), Corporate (contracts/litigation) deepen after Stage 2 trust bar.

### 6.6 Billing

**Must:** Preserve existing Starter / Growth / Professional fair-use model.  

**Should:** Practice fee ledger and GST-capable client invoices later.  

**May:** Time tracking; optional posting of collected fees into MitraBooks accounting at Stage 6 only.

### 6.7 Advanced AI providers

**Must:** Optional and gated; no confidential content leaves the tenant boundary without policy + user authorization + audit; retrieved sources visually distinct from model analysis; provider failure falls back to safe insufficient-source behavior—never silent uncited advice.

### Traceability IDs (safety / stage exits only)

| ID | Requirement |
| --- | --- |
| LM-TRUST-1 | Research answers always include confidence + citations or refusal + advisory + human-review flag |
| LM-TRUST-2 | No fabricated statutory or case citations |
| LM-TRUST-3 | Advanced AI production enablement requires explicit gate checklist |
| LM-SCOPE-1 | Stage 2 corpus priority = GST + Income Tax (narrow slice first) |
| LM-SCOPE-2 | LegalMitra remains separate from MitraBooks ERP frontend |
| LM-TENANT-1 | Tenant and product isolation on all private practice/research data |

---

## 7. Professional Intelligence (product behavior)

Product shape—not library choice:

```text
                    Intent routing
                          │
     Research · Tax/Compliance · Drafting · Documents · Matter · Calendar
                          │
              Always return sources, confidence, or refusal
```

Near term: improve the existing research path; do not claim multi-agent production behavior. Shared intelligence across SanMitra products is Stage 6.

Safety product rules:

- No fabricated citations  
- Human review required for generated legal content  
- Jurisdiction explicit or blocked  
- Staleness / source-date honesty  
- Retention and confidentiality honored  
- Soft-archive legal records unless erasure policy requires otherwise  

Do not chase zero hallucination. Chase **high precision, grounded citations, transparent uncertainty, refusal on weak evidence**.

---

## 8. Information Architecture

**Current surfaces to preserve while evolving:** home research, chat, templates, tracker (honest labeling), pricing, Insights, auth, public pages.

**Target authenticated workspace:**

```text
Home / Morning Brief
AI Workspace
Practice → Clients · Matters · Calendar · Tasks
Knowledge
Templates & Forms
Compliance (persona pack)
Billing
Insights
Settings
```

Ship new workspace areas incrementally without breaking the live research and marketing experience.

---

## 9. Roadmap and Stage Success Criteria

Near-term stages matter more than decade vision. **Do not start Stage 3+ until Stage 2 quality holds and LegalMitra has meaningfully more than one paying user.** Do not spread AI build across the other three SanMitra products until Stage 6.

### Stage Now — Adoption

**Build:** Reliable research or template path; honest labeling of stubs; live baseline stays green; AI investment stays on LegalMitra.

**Stage Now is complete when:**

- At least one end-to-end workflow (research **or** template) works reliably with plan limits.  
- Demo surfaces do not present fake practice metrics as live data.  
- Live LegalMitra baseline remains green.

### Stage 2 — Knowledge Platform

**Build:** Hybrid research with citations and refusal for **GST + Income Tax** (narrow subdomain first); answer feedback and quality metrics; launch-grade templates in parallel; optional early Morning Brief demo; advanced AI remains gated.

**Current engineering status (2026-08-01):** Local Stage 2 trust gate is met for the GST §54 / IT §139 offline slices — response contract, answer feedback, eval fixture (**20/20**, grounding 100%), and local statute ingest (CGST 164 + rules 126 + IT 1961 458 sections, no embeddings yet). Tracker preview labeling is honest. Staging `LEGAL_RAG_ENABLED` flip and Gemini `--embed` remain operator steps (see staging RAG verification runbook). Launch-grade template quality gate and Morning Brief demo remain parallel/optional and are **not** required to claim the Stage 2 research trust bar.

**Planned Stage 2.1 (partially implemented 2026-08-01):** Named Quality Gate + statute-first Citation Audit are wired on the hybrid research path (`quality_gate` / `citation_audit` on responses; unsupported section numbers refuse). Remaining: broader claim segmentation, case-law citators, eval fault fixtures expansion. Spec: [`docs/architecture/LEGALMITRA_STAGE2_1_QUALITY_GATE_AND_CITATION_AUDIT.md`](../architecture/LEGALMITRA_STAGE2_1_QUALITY_GATE_AND_CITATION_AUDIT.md).

**Stage 2 is complete when:**

- Citation grounding on the GST/IT eval set is **≥ 95%** (answers cite only retrieved/authorized sources, or refuse).  
- Refusal works correctly on weak-evidence and missing-jurisdiction cases.  
- Every research answer shows confidence, advisory notice, and human-review required.  
- Citation accuracy and refusal rates are instrumented and reviewable.  
- Live baseline remains green.  
- **Adoption gate to Stage 3:** meaningfully more than one paying user **and** sustained usage (target: daily active usage among paid users **> 40%** over a measured window). If the 50-paying-user ambition is the commercial goal, treat it as a go-to-market target parallel to Stage 2—not a substitute for the trust metrics above.

### Stage 3 — Matter / Client Intelligence

**Build:** Real clients and matters; documents on matters; persona workspace with real data; matter briefs with sources/limitations.

**Current engineering status (2026-08-02):** Stage 3 foundation is in progress in-repo: Mongo-backed Clients/Matters/Documents/Timeline/Briefs/Dashboard under `/api/v1/legal/*`, with matter status lifecycle, auto matter numbers, structured Matter Intelligence Briefs, and tracker live widgets when authenticated. Spec: [`docs/architecture/LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](../architecture/LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md). Adoption gate (multi-user paid usage) remains a commercial go/no-go parallel to engineering readiness.

**Stage 3 is complete when:**

- Practice data persists per tenant and survives refresh (no localStorage system-of-record).  
- Opening a matter shows a human-reviewed intelligence summary with sources or clear limitations.  
- Persona switch changes the workspace using real entitlements and data.

### Stage 4 — Proactive Assistant

**Build:** Production Morning Brief; deadline/limitation/filing watches; compliance-gap and practice-area notification alerts.

**Planned engineering status (2026-08-02):** Implementation plan and foundation code in [`docs/architecture/LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md`](../architecture/LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md) — deterministic alerts, Practice Health Score, Morning Brief, in-app notifications, tracker panel. Feature-flagged via `LEGALMITRA_PROACTIVE_ENABLED`.

**Stage 4 is complete when:**

- Morning Brief is generated only from the user’s real tenant data.  
- At least one proactive alert type (deadline or compliance gap) is trusted enough for daily use.  
- Professionals can act on brief items without leaving the workspace for the common path.

### Stage 5 — Agentic Workflows

**Build:** Multi-step prepare/research/draft/check flows with human sign-off; knowledge-graph MVP for proven act families.

**Stage 5 is complete when:**

- One end-to-end agentic workflow runs with audit trail and mandatory human approval gates.  
- No filing or client-facing send occurs without explicit human confirmation.  
- Graph- or relation-aware retrieval improves precision on a defined eval set versus Stage 2 baseline.

### Stage 6 — Platform Ecosystem

**Build:** Shared SanMitra intelligence/document/notification patterns where justified; optional MitraBooks fee posting; selective practice-OS parity only where it serves the north star.

**Stage 6 is complete when:**

- A shared capability is reused by LegalMitra without duplicating unsafe AI paths.  
- Any accounting posting uses the shared accounting path only—no direct ledger mutation from LegalMitra.  
- LegalMitra remains a distinct product experience.

### Immediate next steps

1. Keep AI/RAG scoped to LegalMitra research.  
2. Prove hybrid research on GST refund provisions (or approved alternate).  
3. Instrument citation accuracy and refusal from day one of Stage 2.  
4. Demo Dynamic Workspace / Morning Brief early without claiming Stage 4 completion.  
5. Revisit Stage 3+ only after the Stage 2 trust and adoption gates.

---

## 10. Non-Functional Product Requirements

| Area | Requirement |
| --- | --- |
| Security | No secrets in product artifacts; no logging of tokens/passwords; provider use audited |
| Privacy | Tenant retention; soft-archive; DPDP-aware handling |
| Isolation | All private data tenant- and product-scoped |
| Reliability | Provider outages degrade to safe refusal, not invented law |
| Quality over raw speed | Prefer grounded answers over fast uncited ones |
| Honesty in releases | Distinguish current vs target vs gap in every release note |
| Testing | Isolation, attribution, refusal, review gates, and live baseline coverage for changed risk |

Implementation commands, CI, and module keys belong in the Architecture Specification and platform developer docs—not here.

---

## 11. Competitive Lens (Legalit as benchmark)

| Dimension | Benchmark | LegalMitra |
| --- | --- | --- |
| Practice management breadth | High | Selective, later stages |
| Daily login stickiness | Strong | Adopt Morning Brief + practice loop |
| AI | Feature-oriented | Trust-first Professional Brain |
| Knowledge graph / matter intelligence | Limited or not evident | Planned differentiators |
| Multi-persona (CA/CS/Corporate) | Advocate-centric | Explicit design |
| Citation / refusal rigor | Not brand-defining | Must-win |

---

## 12. Risks

| Risk | Mitigation |
| --- | --- |
| Live regression | Stage gates; feature flags; preserve baseline |
| Hallucinated law | Trust contract + refusal + eval set |
| Scope explosion | “Not Now” list + Legalit-as-benchmark rule |
| Confidential leakage to providers | Default deny + policy + audit |
| Thin corpus | GST + IT first; expand only after eval bar |
| Persona breadth without depth | Multi-persona shell early; deep packs after Stage 2 |
| Premature multi-product AI | Stage 6 only |
| Accounting contamination | Practice billing separate; shared ledger only via accounting path |

---

## 13. Acceptance for Work Derived from This PRD

- [ ] Describes current / target / gap honestly  
- [ ] Preserves tenant and product isolation  
- [ ] Keeps generated legal output draft/advisory with human review  
- [ ] Citations are source-backed or the product refuses  
- [ ] Does not silently enable advanced AI in production  
- [ ] Does not merge LegalMitra into MitraBooks ERP or pull InvestMitra into scope  
- [ ] Does not violate the “Not Now” list without explicit owner decision  
- [ ] Includes tests for the risk area changed  
- [ ] Live LegalMitra baseline remains green (or exception documented)

---

## 14. Open Questions

1. Confirm Stage 2 narrow slice: GST refund / Section 54 family—or name an alternate.  
2. Confirm commercial adoption targets for the Stage 2→3 gate (paying users and daily active usage window).  
3. Practice invoices LegalMitra-native until Stage 6—approve?  
4. Keep the Implementation Blueprint as living vision, and expand the outline-only Architecture Blueprint only if needed—approve?  

Stack choices (vector store, BM25 engine, orchestrator) are decided in the Architecture Specification, not this PRD.

---

## 15. Document Control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-07-31 | First engineering PRD from repo + planning transcript |
| 1.1 | 2026-07-31 | Aligned to Vision & Implementation Blueprint stages |
| 2.0 | 2026-07-31 | Review refinements: North Star, product/implementation split, fewer IDs, stage success criteria, elevated Not Now list; tech moved to Architecture Spec |

**Vision source:** LegalMitra Vision & Implementation Blueprint.  
**Implementation source:** [LegalMitra Architecture Specification](../architecture/LEGALMITRA_ARCHITECTURE_SPEC.md).  
**Platform constraints:** SanMitra unified platform PRD and operating policy remain controlling where they conflict; resolve conflicts explicitly before coding.

This is a **living document**. Update when product direction changes; resist turning it back into a 100-page specification.
