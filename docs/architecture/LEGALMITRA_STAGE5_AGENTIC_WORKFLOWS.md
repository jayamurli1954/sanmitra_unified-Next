# LegalMitra Stage 5 — Agentic Workflows

**Document type:** Implementation specification  
**Product:** LegalMitra  
**Status:** Planned (not yet implemented)  
**Version:** 1.1  
**Date:** 2026-08-02  
**Companion PRD:** [`docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md`](../prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md)  
**Depends on:**  
- Stage 2 research trust ([`LEGALMITRA_RAG_RESPONSE_CONTRACT.md`](LEGALMITRA_RAG_RESPONSE_CONTRACT.md), Stage 2.1 quality gate)  
- Stage 3 practice context ([`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md))  
- Stage 4 proactive surfaces ([`LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md`](LEGALMITRA_STAGE4_PROACTIVE_ASSISTANT.md))

This document is the engineering contract for **Stage 5 (Agentic Workflows)**.  
It introduces **one** multi-step prepare → research → draft → check flow with mandatory human sign-off, plus a **narrow** knowledge-graph MVP that **enriches** Stage 2 retrieval — not a general autonomous legal agent platform.

Review additions in v1.1: workflow templates + catalog, run timeline events, `estimated_minutes`, per-step confidence, retry classes, Morning Brief → recommended workflow CTA, completion analytics, inverted KG placement (research enrichment only), and explicit bans on agent-to-agent / self-modifying workflows.

---

## 1. Why Stage 5 exists (product progression)

| Stage | What it established |
| --- | --- |
| 2 | **Trust** — grounded research, citations, refusal |
| 3 | **Context** — clients, matters, documents, timeline |
| 4 | **Proactivity** — Morning Brief, alerts, act-in-place |
| **5** | **Guided execution** — multi-step workflows with human control |

Stage 5 answers: *“Help me prepare this matter step by step — but I remain in control.”*

Product posture: **AI Professional Assistant**, not “AI Lawyer.”  
Never jump from RAG to autonomous agents.

---

## 2. Current vs target vs gap

| Layer | Current state | Target (Stage 5) | Gap |
| --- | --- | --- | --- |
| Research | Hybrid research (Stage 2) | A **step** inside a workflow; KG may enrich retrieval | Workflow runner + adapters |
| Matter context | Stage 3 CRUD + briefs | Bound to `workflow_run` | Matter-scoped run state |
| Alerts / Morning Brief | Stage 4 | **Recommended Workflow** one-click start | Alert → catalog mapping |
| Orchestration | None | Declared step graph + state machine | `legal_workflow_*` |
| Agents | None | Specialist **service adapters** only | Adapter interfaces |
| Knowledge graph | Seeds / crosswalk | Enrich Stage 2 RAG for approved families | Nodes/edges + eval |
| Human gates | Review flags | Explicit approve / reject / revise | Gate API + UI |
| File / send | Not automated | Still never automatic | Hard deny |

**Non-goals (Stage 5) — do not build:**

- Autonomous filing (GST / IT / MCA / e-courts)  
- Auto-email / WhatsApp to clients without explicit confirm  
- Agent-to-agent conversations  
- Autonomous planning loops  
- Dynamic tool discovery  
- Self-modifying workflows  
- General multi-agent swarm / LangGraph platform rewrite  
- Replacing Stage 2 research UX or Stage 4 Morning Brief  
- Full Legalit practice OS; MitraBooks fee posting (Stage 6)  
- Graphing “all Indian law”  

The workflow graph stays **deterministic and auditable**.

---

## 3. Prerequisites

1. Stage 3 + Stage 4 stable (matters, timelines, alerts, Morning Brief).  
2. Stage 2 citation/refusal gates green.  
3. `LEGALMITRA_AGENTIC_ENABLED` (default **false** in production).  
4. Platform-owner approval before any paying tenant enablement.  

---

## 4. Workflow Catalog (product roadmap)

Engine stays the same; catalog communicates what exists vs planned.

| Workflow | `workflow_key` | Status |
| --- | --- | --- |
| Prepare Matter Response | `prepare_matter_response` | **MVP** |
| Hearing Preparation | `hearing_preparation` | Planned |
| Contract Review | `contract_review` | Planned |
| GST Notice Reply | `gst_notice_reply` | Planned (template on MVP engine) |
| Income Tax Notice | `income_tax_notice` | Planned (template on MVP engine) |
| ROC Filing Review | `roc_filing_review` | Planned |

`GET /workflows/catalog` returns this list with `status: mvp | planned | disabled`.

---

## 5. MVP workflow + templates

### 5.1 Engine MVP: **Prepare Matter Response**

```text
Trigger (Morning Brief “Recommended Workflow” OR manual Prepare)
  → INTAKE           Confirm matter facts, jurisdiction, deadline
  → RESEARCH         Stage 2 hybrid research (+ optional KG enrichment)
  → EVIDENCE_CHECK   Checklist vs attached documents / gaps
  → DRAFT            Advisory outline / template-assisted draft
  → HUMAN_REVIEW     Mandatory approve / revise / reject
  → COMPLETE         Persist artifacts; optional human “ready to file” marker only
```

**Hard rule:** COMPLETE never files and never sends.

### 5.2 `workflow_template` (same engine, different packs)

Reserved on definitions / runs so new packs do not fork the engine:

| `workflow_template` | Examples of pack differences |
| --- | --- |
| `gst_notice` | GST checklist + research query seeds |
| `income_tax_notice` | IT §139-family seeds |
| `section_138` | NI Act checklist (later) |
| `consumer_complaint` | Later |
| `employment_contract` | Later |
| `board_resolution` | Later |
| `general` | Default MVP |

MVP ships `general` + optionally `gst_notice` / `income_tax_notice` if Stage 2 corpus already covers them.

### 5.3 Specialist adapters (not separate products)

| Adapter | Role |
| --- | --- |
| Matter | Load matter, client, dates, timeline |
| Alerts | Read Stage 4 alert that triggered the run |
| Research | Stage 2 `build_hybrid_legal_response` |
| Knowledge Graph | **Enrich** research retrieval only (optional) |
| Document | Doc list + gap checklist |
| Drafting | Template/outline; always human-review |
| Tax / Compliance | Optional persona checklist hints |

Orchestrator follows the **declared** definition — no free-form tool calling in MVP.

---

## 6. Knowledge graph placement (structural rule)

**Do not** treat the graph as the primary source of truth.

Correct order:

```text
Workflow
  → Research step
      → Knowledge Graph enrichment (optional rerank / related nodes)
      → Stage 2 RAG / hybrid retrieval (contract remains authoritative)
      → Grounded answer or refusal
  → Draft (from approved research + matter context)
```

Wrong order (forbidden for MVP):

```text
Knowledge Graph → Workflow as primary authority
```

On graph miss: degrade to Stage 2 path. Never invent edges or citations.

---

## 7. State machine, retries, confidence, time

### 7.1 Run status

| Status | Meaning |
| --- | --- |
| `draft` | Created, not started |
| `running` | A step is in progress |
| `awaiting_human` | Blocked on approval gate |
| `completed` | Required approvals done |
| `cancelled` | User cancelled |
| `failed` | Terminal failure (see retry class) |

### 7.2 Step status

`pending` → `running` → `succeeded` | `failed` | `awaiting_human` → `approved` | `rejected` | `revised`

`RESEARCH` and `DRAFT` (and any future FILE/SEND placeholders) **must** hit `awaiting_human` before the run can complete.

### 7.3 Failure / retry class

Every failed step records `failure_class`:

| Class | Meaning | UX |
| --- | --- | --- |
| `retryable` | Transient (timeout, provider blip) | “Retry step” |
| `requires_human` | Ambiguous jurisdiction, weak evidence, policy block | Force human decision |
| `permanent` | Invalid matter, missing required intake | Cancel or fix intake |

### 7.4 Per-step confidence

Each succeeded step stores `confidence` (0–1), not only a run-level score.

Examples: Research 0.98, Draft 0.91, Checklist 1.0, KG enrichment 0.95 (when used).  
Research confidence must come from Stage 2 contract fields.

### 7.5 `estimated_minutes`

Each step definition includes `estimated_minutes` for UX (“Research ~6 min”).  
Store `started_at` / `finished_at` on attempts for actual duration analytics.

### 7.6 Idempotency

- `step_attempt_id` per execution  
- Re-run creates a new attempt; prior artifacts remain auditable  
- Research reuses Stage 2 response contract  

---

## 8. Data model (MongoDB)

Scoped by `tenant_id` + `app_key`. Never trust `tenant_id` from request body.

### 8.1 `legal_workflow_definitions`

| Field | Notes |
| --- | --- |
| `workflow_key`, `version` | Identity |
| `workflow_template` | Pack key (§5.2); default `general` |
| `display_name`, `catalog_status` | `mvp` / `planned` / `disabled` |
| `steps[]` | `step_key`, adapter, `requires_human_gate`, `estimated_minutes` |
| `allowed_practice_areas` | e.g. gst, income_tax |
| `enabled` | Runtime flag |

### 8.2 `legal_workflow_runs`

| Field | Notes |
| --- | --- |
| `run_id`, `workflow_key`, `workflow_version`, `workflow_template` | Pin definition |
| `matter_id`, `client_id`, `alert_id` | Links |
| `recommended_from` | `morning_brief` / `alert` / `manual` |
| `status`, `persona` | §7.1; persona presentation-only |
| Timing / analytics snapshot | `started_at`, `completed_at`, `total_duration_ms`, counts of approvals / rejections / revisions / retries |
| Actor timestamps | `created_by`, `created_at`, `updated_at` |

### 8.3 `legal_workflow_steps`

| Field | Notes |
| --- | --- |
| `step_id`, `run_id`, `step_key`, `attempt` | Identity |
| `status`, `failure_class` | §7.2–7.3 |
| `confidence`, `estimated_minutes` | §7.4–7.5 |
| `input_ref`, `output_ref` | Artifacts |
| Human gate fields | `human_review_required`, `approved_by`, `approved_at`, `rejection_reason` |
| `error` | Safe message (no secrets) |
| `started_at`, `finished_at` | Duration |

### 8.4 `legal_workflow_artifacts`

| Field | Notes |
| --- | --- |
| `artifact_id`, `run_id`, `step_id` | Identity |
| `artifact_type` | `research_response` / `checklist` / `draft` / `note` |
| `payload`, `sources` | Research embeds Stage 2 contract |
| `human_review_required` | Always true for drafts |
| `retention` | LegalMitra retention policy |

### 8.5 `legal_workflow_timeline`

Append-only run activity (also mirrors into matter timeline when useful):

```text
run_started → intake_finished → research_finished → draft_generated
  → human_approved | human_rejected | step_retried → run_completed | run_cancelled
```

| Field | Notes |
| --- | --- |
| `event_id`, `run_id`, `matter_id` | Identity / link |
| `event_type`, `summary`, `actor_id`, `occurred_at` | Chronology |
| `payload` | step_key, attempt, optional metrics |

### 8.6 Knowledge-graph MVP (narrow)

| Collection | Purpose |
| --- | --- |
| `legal_kg_nodes` | Act / section / notification / circular for **approved families only** (CGST §54 and/or IT §139 first) |
| `legal_kg_edges` | `amends`, `explains`, `cites`, `supersedes`, `related_to` |

Reserved: `confidence`, `effective_from`, `effective_to`, `jurisdiction`.  
Eval required before claiming precision gain vs Stage 2 baseline.

### 8.7 `legal_workflow_analytics` (or denormalized on run)

On completion, record: time taken, steps executed, human approvals, rejections, revisions, retries, completion vs cancel. Foundation for later optimization — no vanity dashboards required in MVP beyond run detail.

---

## 9. Stage 4 integration — Recommended Workflow

When Morning Brief / alert shows e.g. “GST appeal — deadline tomorrow”:

```text
Recommended Workflow: Prepare Matter Response
[ Start ]   → POST /workflows/runs
              { workflow_key, workflow_template: "gst_notice", matter_id, alert_id,
                recommended_from: "morning_brief" }
```

Mapping uses Stage 4 `recommended_action` / `alert_type` / `practice_area` as **hints**, not autonomous authority.

---

## 10. API surface (`/api/v1/legal`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/workflows/catalog` | Catalog table (§4) |
| GET | `/workflows` | Enabled definitions |
| POST | `/workflows/runs` | Start run |
| GET | `/workflows/runs/{run_id}` | Run + steps + health |
| GET | `/workflows/runs/{run_id}/timeline` | Run timeline events |
| POST | `/workflows/runs/{run_id}/advance` | Next eligible step |
| POST | `/workflows/runs/{run_id}/steps/{step_id}/retry` | Retry if `retryable` |
| POST | `/workflows/runs/{run_id}/steps/{step_id}/approve` | Human approve |
| POST | `/workflows/runs/{run_id}/steps/{step_id}/reject` | Human reject + reason |
| GET | `/workflows/runs/{run_id}/artifacts` | Artifacts |
| GET | `/kg/subgraph` | Read-only MVP subgraph |

Module gate: `legal` (+ `legal_ai` only if provider used). Audit create / advance / approve / reject / retry.

---

## 11. Safety rules (non-negotiable)

1. No file / no send in Stage 5 success path — only human “ready to file” marker.  
2. Research obeys Stage 2 contract (citations, confidence, advisory, refusal).  
3. Drafts always `human_review_required=true`.  
4. Never invent hearings, statutes, court dates, or graph edges.  
5. Provider use of confidential docs only with tenant policy + user authorization.  
6. Tenant isolation on runs / steps / artifacts / timeline / graph queries.  
7. Soft-cancel; keep audit + timeline.  
8. Deterministic declared workflows only — no self-modifying graphs.  

---

## 12. Frontend surfaces

- Morning Brief Priority Action: **Recommended Workflow** + Start  
- Workflow run panel: steps with estimated vs actual minutes, per-step confidence, Approve / Revise / Reject / Retry  
- Artifact viewer (research / checklist / draft)  
- Run timeline strip  
- Preserve research chat + templates; do not force all work through workflows  
- Persona switch remains presentation-only  

---

## 13. Acceptance criteria

### Workflow exit

- [ ] One E2E `prepare_matter_response` completes with audit + timeline  
- [ ] RESEARCH and DRAFT cannot complete without human approve  
- [ ] Failed research refuses safely (no fabricated citations)  
- [ ] Retryable vs requires_human vs permanent failures behave correctly  
- [ ] Per-step confidence and estimated_minutes present on definitions/steps  
- [ ] Morning Brief can start a recommended workflow in one click  
- [ ] No API path files or sends client communications  
- [ ] Tenant isolation verified  
- [ ] Feature flag disables agentic routes in production  
- [ ] Stage 2, 3, and 4 tests still pass  

### Knowledge-graph MVP exit

- [ ] Restricted to approved act family(ies)  
- [ ] Used only as research enrichment (§6)  
- [ ] Graph miss → Stage 2 path  
- [ ] Eval documents precision vs Stage 2 baseline before claiming improvement  

---

## 14. Implementation sequence

| Step | Work | Outcome |
| --- | --- | --- |
| 0 | Stage 3/4 stable + flags | Safe base |
| 1 | Definitions, catalog, templates, run/step/artifact/timeline schemas | Data layer |
| 2 | Orchestrator + Matter/Research/Document adapters + retry classes | Skeleton |
| 3 | Human gates + per-step confidence + tests | Safety core |
| 4 | Drafting adapter + artifacts | Full MVP path |
| 5 | Morning Brief recommended-workflow CTA | Stage 4 bridge |
| 6 | KG enrichment hook (optional) + subgraph API | Graph slice |
| 7 | Analytics snapshot on completion + eval vs Stage 2 | Evidence |
| 8 | Run panel UI + preflight / regression | Exit |

---

## 15. Explicitly deferred

| Topic | When |
| --- | --- |
| Portal auto-filing | Separate approved stage only |
| Full workflow marketplace UI | After MVP proven |
| Agent-to-agent / autonomous planners | Much later (if ever) |
| Broad case-law graph | After statute-family MVP |
| Shared SanMitra agent bus / MitraBooks posting | Stage 6 |

---

## 16. Document control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-08-02 | Initial Stage 5 plan |
| 1.1 | 2026-08-02 | Review: templates, catalog, timeline, estimates, per-step confidence, retry classes, recommended workflow CTA, analytics, KG enrichment order, ban autonomous agent loops |
