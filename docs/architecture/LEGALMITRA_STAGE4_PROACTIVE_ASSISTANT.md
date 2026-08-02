# LegalMitra Stage 4 — Proactive Assistant

**Document type:** Implementation specification  
**Product:** LegalMitra  
**Status:** Active implementation target  
**Version:** 1.1  
**Date:** 2026-08-02  
**Companion PRD:** [`docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md`](../prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md)  
**Depends on:** [`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md)

This document is the engineering contract for **Stage 4 (Proactive Assistant)**.  
It stays faithful to the PRD roadmap: Morning Brief and deadline/compliance alerts built on Stage 3 practice data — **not** a full practice OS and **not** Stage 5 agentic workflows.

Review additions in v1.1: Daily Practice Health Score, priority scoring, deterministic suggested actions, dormant-matter alert, matter/client health signals, reserved Stage 5 fields, multi-window brief engine shape, and acceptance updates.

---

## 1. Current vs target vs gap

| Layer | Current state (after Stage 3 foundation) | Target (Stage 4) | Gap |
| --- | --- | --- | --- |
| Practice data | Clients, matters, documents, timeline, matter briefs, dashboard widgets | Same entities as **inputs** to proactive surfaces | Consume Stage 3 APIs; do not redesign them |
| Morning Brief | Optional/demo mention only | Tenant-grounded daily brief + health score | `legal_morning_briefs` + generate/fetch API + UI |
| Deadline watches | Matter hearing/deadline fields | Deterministic alerts as dates approach/pass | Alert rules + materialization |
| Compliance gaps | Ad hoc | Explicit gap + dormant matter alerts | Gap / dormant detectors |
| Notifications | None | In-app inbox | `legal_practice_notifications` |
| Act-in-place | Manual navigation | Deep-links from brief/alert items | Frontend action contracts |
| Stage 5 | Not started | Agentic multi-step flows | **Deferred** |

**Non-goals (Stage 4):**

- Cause-list / court sync  
- Full Legalit-style calendar  
- Email/SMS as the only delivery path (in-app first)  
- MitraBooks fee posting (Stage 6)  
- Multi-agent orchestrator / auto-file / auto-send (Stage 5)  
- Fabricating hearings, statutes, or court dates not present on tenant records  

**Never invent hearings, statutes, or court dates.** That rule is non-negotiable.

---

## 2. Prerequisites

1. Stage 3 practice APIs merged/stable on the working branch.  
2. Stage 3 smoke: client → matter (with dates) → document → matter brief → live tracker widgets.  
3. Stage 2 LegalMitra research trust tests remain green.  

Commercial adoption gate remains a parallel product decision. Proactive surfaces are feature-flagged for production control.

---

## 3. Product behavior

### 3.1 Morning Brief (production)

Generated **only** from real tenant practice data. Empty tenants get an honest empty brief — never demo filler.

### 3.2 Fixed Morning Brief structure

```text
Date / Persona Context
Daily Practice Health Score     (0–100 + label)
Priority Actions                (sorted by Priority Score)
Upcoming Hearings
Upcoming Deadlines
Matters Awaiting Review
Compliance Gaps
Recent Activity
Suggested Focus                 (deterministic suggested next actions)
Limitations
Confidence
Human Review Required
```

### 3.3 Daily Practice Health Score

Single score (0–100) derived deterministically from:

- Open / active matters balance  
- Overdue hearings/deadlines  
- Pending review backlog  
- Missing-document gaps  
- Dormant matters  
- Urgent alerts  

Labels: `Critical` (<50), `Needs Attention` (50–74), `Healthy` (75–89), `Strong` (90–100).

### 3.4 Priority Score (sort key)

Each Priority Action / alert carries a numeric `priority_score` built from:

```text
urgency (overdue / days-to-due)
+ matter priority field
+ practice-area risk weight (light defaults)
+ compliance / missing-doc penalty
+ dormant penalty
= priority_score
```

Morning Brief Priority Actions are always sorted by `priority_score` descending.

### 3.5 Deterministic suggested next actions

Every alert/brief item includes `suggested_actions[]` such as:

- Prepare for hearing / deadline  
- Review last timeline event  
- Attach missing documents  
- Generate Matter Intelligence Brief  
- Follow up with client  

These are rule-based in Stage 4 (not model-generated). Reserved fields `recommended_action` / `recommended_priority` on alerts are stored for Stage 5 enrichment.

### 3.6 Matter Health / Client Health (signals)

Lightweight scores computed on read/brief generation (not a separate product surface yet):

- **Matter Health:** docs present, deadline proximity, recent timeline activity, status, brief freshness  
- **Client Health:** open matters, pending count, overdue alerts on that client  

Surfaced inside Morning Brief / dashboard payload; full widgets can deepen later.

### 3.7 Alert types

| Priority | Alert type | Trigger |
| --- | --- | --- |
| P0 | `deadline_approaching` | `next_deadline_date` overdue or ≤ lookahead days |
| P0 | `hearing_approaching` | `next_hearing_date` overdue or ≤ lookahead days |
| P1 | `compliance_gap_missing_documents` | Active/pending matter with zero documents |
| P1 | `matter_awaiting_review` | Draft/pending older than stale days |
| P1 | `dormant_matter` | Active/pending/on_hold with no timeline activity for N days (default 45) |

Optional checklist gaps (practice-area document expectations) may add payload hints without inventing filings.

### 3.8 Act-in-place

| Action | Target |
| --- | --- |
| Open matter | Tracker / matter deep link with `matter_id` |
| View timeline | Matter timeline |
| Generate Matter Brief | Stage 3 brief endpoints |
| Attach document | Stage 3 documents endpoints |
| Dismiss / snooze alert | Alert PATCH |

No filing or client-facing send.

### 3.9 Multi-window briefs (same engine)

`window` parameter: `daily` (MVP), with reserved support for `weekly` / `monthly` / `quarterly` using the same generator and different date windows. Only `daily` is required for Stage 4 exit.

Trend intelligence (research time, revenue, win rate) is **reserved / deferred** — simple counts only if cheap; no fabricated analytics.

---

## 4. Data model (MongoDB)

Scoped by `tenant_id` + `app_key`. Never trust `tenant_id` from request body.

### 4.1 `legal_practice_alerts`

| Field | Notes |
| --- | --- |
| `alert_id`, `tenant_id`, `app_key` | Identity / isolation |
| `alert_type`, `severity`, `status` | open / snoozed / resolved / dismissed |
| `matter_id`, `client_id` | Optional FKs |
| `title`, `summary` | Display |
| `due_at`, `dedupe_key` | Watch + anti-spam |
| `priority_score` | Sort key |
| `suggested_actions` | list[str] |
| `recommended_action` | Reserved string for Stage 5 (may mirror first suggested action) |
| `recommended_priority` | Reserved string/int for Stage 5 |
| `matter_health`, `client_health` | Optional snapshot ints |
| `payload`, `snoozed_until`, resolve metadata, timestamps | |

Also reserve (no behavior yet): `channel_prefs`, `assignee_user_id`, `external_calendar_ref`.

### 4.2 `legal_practice_notifications`

User-scoped inbox: `notification_id`, `user_id`, `source_type`, `source_id`, `title`, `body`, `action_href`, `read_at`, timestamps.

### 4.3 `legal_morning_briefs`

| Field | Notes |
| --- | --- |
| `brief_id`, `tenant_id`, `app_key`, `user_id` | Isolation |
| `brief_date`, `window`, `persona` | daily MVP; weekly+ reserved |
| `practice_health_score`, `practice_health_label` | 0–100 + label |
| `sections` | Fixed structure including health + suggested focus |
| `alert_ids`, `matter_ids`, `sources` | Provenance |
| `advisory_notice`, `confidence`, `human_review_required` | Always advisory |
| `generation_strategy` | `grounded_practice_summary` |
| `generated_at`, `generated_by` | |

Uniqueness: `(tenant_id, app_key, user_id, brief_date, persona, window)` unless `force_refresh`.

### 4.4 Feature flags

- `LEGALMITRA_PROACTIVE_ENABLED`  
- `LEGALMITRA_ALERT_LOOKAHEAD_DAYS` (default 7)  
- `LEGALMITRA_DORMANT_MATTER_DAYS` (default 45)  
- `LEGALMITRA_MORNING_BRIEF_ENABLED`  

Assembly strategy notes (deterministic vs optional provider enrichment) live in the Architecture Specification — not as model-selection requirements in this product plan.

---

## 5. Alert evaluation

Runs on Morning Brief generation and `POST /practice/alerts/refresh`.

```text
for each non-closed/archived matter:
  deadline/hearing within lookahead → upsert P0 alerts
  active/pending + zero docs → missing documents
  draft/pending + age ≥ stale_days → awaiting review
  active/pending/on_hold + no timeline ≥ dormant_days → dormant_matter
```

Auto-resolve when condition clears; or user snooze/dismiss with audit.

---

## 6. API surface (`/api/v1/legal`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET/POST | `/practice/morning-brief` | Fetch / regenerate (window=daily) |
| GET | `/practice/alerts` | List alerts (sorted by priority_score) |
| POST | `/practice/alerts/refresh` | Re-evaluate |
| PATCH | `/practice/alerts/{id}` | Snooze / dismiss / resolve |
| GET | `/practice/notifications` | Inbox |
| PATCH | `/practice/notifications/{id}/read` | Mark read |
| GET | `/practice/dashboard` | Extend with open_alerts + health score |

---

## 7. Frontend

- Tracker / authenticated shell: Morning Brief panel with health score + Priority Actions  
- Deep links with `matter_id`  
- Open-alerts metric on tracker  
- Minimal notification list (optional stretch)  
- Persona switch remains presentation-only  

---

## 8. Safety

- Ground only on tenant practice records.  
- Never invent hearings, statutes, or court dates.  
- Always `human_review_required` + advisory notice on Morning Briefs.  
- No auto-send / auto-file.  
- Soft-resolve; audit mutations.  
- Tenant isolation tests required.

---

## 9. Implementation sequence

1. Schemas + indexes  
2. Alert evaluator (P0 + dormant + missing docs)  
3. Health / priority scoring  
4. Morning Brief generator  
5. Notifications  
6. Routes + dashboard extensions  
7. Frontend Morning Brief + tracker metrics  
8. Tests + Stage 2/3 regression  

---

## 10. Acceptance criteria

- [ ] Morning Brief from real tenant data only; empty tenant honest  
- [ ] Practice Health Score present on brief  
- [ ] Priority Actions sorted by `priority_score`  
- [ ] P0 deadline or hearing alert works including overdue  
- [ ] Dormant matter alert evaluates  
- [ ] Suggested actions present on alerts/brief items  
- [ ] Tenant isolation verified  
- [ ] Snooze/dismiss audited  
- [ ] Act-in-place deep link works  
- [ ] Feature flag can disable proactive generation  
- [ ] Stage 2 and Stage 3 tests still pass  

---

## 11. Deferred (explicit)

| Topic | When |
| --- | --- |
| Weekly/Monthly/Quarterly brief UI | After daily MVP |
| Full Client Health / Matter Health widgets | Post-MVP |
| Trend intelligence (time, revenue, win rate) | Later |
| Practice-area mandatory document packs (rich) | Later |
| Stage 5 use of `recommended_action` | Stage 5 |
| Email/SMS push | After in-app |
| Agentic workflows / MitraBooks fees | Stages 5–6 |

---

## 12. Document control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-08-02 | Initial Stage 4 plan |
| 1.1 | 2026-08-02 | Review enhancements: health score, priority score, suggested actions, dormant alert, reserved Stage 5 fields, multi-window shape |
