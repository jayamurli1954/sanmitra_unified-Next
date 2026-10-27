# MitraBooks — AI Capture → Auto-Categorize → Confidence-Routed Posting (Add-on Design)

Status: **Draft / scoped design** · Owner: MitraBooks · Date: 2026-10-27
Supersedes nothing. Extends: OfficeMitra AI layer, the cross-document approval queue, bank reconciliation, and payment allocation.

---

## 1. Why this add-on

Competitor "autonomous bookkeeper" offerings (accrualis et al.) sell one thing MitraBooks does
not yet do: an **autonomous ingestion front-end** — AI reads bills/receipts from email and
WhatsApp, categorizes them, and only escalates low-confidence items to a human. MitraBooks already
owns the *hard back-end* pieces this needs:

- the **AI orchestrator** (provider abstraction, prompt versioning, telemetry) —
  [`app/modules/office_ai/ai/orchestrator.py`](../../app/modules/office_ai/ai/orchestrator.py)
- the **cross-document approval queue** that already surfaces `pending_approval` documents —
  [`app/modules/business/services/approval_queue.py`](../../app/modules/business/services/approval_queue.py)
- **payment ↔ bill / invoice ↔ receipt allocation** —
  [`app/modules/business/allocation_service.py`](../../app/modules/business/allocation_service.py)
- **bank reconciliation** (metadata-only match + explicit confirm) —
  [`app/modules/business/bank_recon.py`](../../app/modules/business/bank_recon.py)
- the **OfficeMitra document queue / review notes / tasks** machinery —
  [`app/modules/office_ai/services/documents_service.py`](../../app/modules/office_ai/services/documents_service.py)

What is missing is the glue: a **capture → extract → validate → score → route** pipeline that turns
an inbound document into a *drafted* MitraBooks voucher/bill/invoice, and lets confidence decide
whether a human must look at it. This design adds exactly that glue and reuses everything above.

**Non-goal (explicit):** this is **not** a license to auto-post blindly at "99% confidence."
MitraBooks' control posture (see §7 and the
[Bank Feed Policy](../operations/MITRABOOKS_BANK_FEED_POLICY.md)) is a product differentiator, not a
limitation. AI confidence never bypasses deterministic validation, and auto-posting is a separate,
off-by-default decision.

---

## 2. Scope

### In scope
- Inbound **capture** from: manual upload, email mailbox, WhatsApp (BSP webhook), and the existing
  OfficeMitra CA document queue.
- **AI + OCR extraction** of structured fields (vendor/customer, date, amounts, tax, line items,
  GSTIN, invoice number) from PDFs/images/email bodies.
- **Deterministic validation** (arithmetic, GSTIN format, duplicate fingerprint, party resolution,
  GL account mapping, period lock).
- A **blended confidence score** (extraction signal × validation outcome).
- **Confidence routing**: high-confidence → drafted document ready for one-click approval (or
  auto-post only when the aggressive flag is on and policy allows); low-confidence → human review
  with extracted fields + source attached.
- **Posting** through the *existing* typed voucher / purchase-bill / sales-invoice services — no new
  journal path.
- **Auto-match / reconcile** reusing allocation + bank recon (metadata-only, confirmation-gated by
  default).

### Out of scope (this iteration)
- Live bank-feed provider connectors (governed separately by the Bank Feed Policy; this add-on
  consumes statement lines that already exist, it does not add feeds).
- Payment initiation / fund transfer / mandate creation (permanently out — see policy Non-Goals).
- Any write to the GL that does not pass through the typed voucher/approval workflow.

---

## 3. Architecture overview

```
 Capture sources                 Pipeline (new: app/modules/business/capture/)            Reuse
 ────────────────                ─────────────────────────────────────────────           ─────
 Manual upload ─┐
 Email mailbox ─┤                ┌──────────┐  ┌──────────┐  ┌──────────┐
 WhatsApp (BSP)─┼──► CaptureItem ►│ Extract  │─►│ Validate │─►│  Score   │
 CA doc queue  ─┘   (new coll.)   │ AI + OCR │  │ (determ.)│  │ (blend)  │
                                  └────┬─────┘  └────┬─────┘  └────┬─────┘
                                       │ orchestrator│ GST/COA     │
                                       ▼ pattern     ▼ helpers     ▼
                                  ┌─────────────────────────────────────┐
                                  │            Route by confidence       │
                                  └───────────────┬─────────────────────┘
                              high + valid │                 │ low / failed-validation
                                           ▼                 ▼
                             Draft typed document      Human review
                             (pending_approval)         (extracted fields + source doc)
                                           │                 │
                                           ▼                 ▼
                           ┌──────────────────────────────────────────┐
                           │  EXISTING cross-document approval queue    │  ◄── reuse
                           │  approval_queue.list_documents_for_...     │
                           └───────────────┬────────────────────────────┘
                                           ▼ on approve (human or auto-post flag)
                           ┌──────────────────────────────────────────┐
                           │ EXISTING posting services (voucher/bill/   │  ◄── reuse
                           │ invoice) → journal → allocation + recon    │
                           └──────────────────────────────────────────┘
```

Key principle: **the pipeline produces documents, not journal entries.** It stops at
`pending_approval`. Promotion to `posted` happens through the unchanged approval/posting path, so
every control (period locks, approval rules, audit, reversal) applies automatically.

---

## 4. Pipeline stages

### 4.1 Capture → `CaptureItem`
Every source normalizes into one `CaptureItem` record (new `capture_items` collection), scoped by
`tenant_id` + `app_key` + `accounting_entity_id` (same scoping as the approval queue and bank
recon). A **content fingerprint** (hash of source bytes + sender + amount hints) provides idempotent
dedupe, mirroring the bank-recon dedupe-fingerprint rule.

Source adapters:
- **Upload**: direct API / existing document upload.
- **Email**: a dedicated per-tenant ingest alias; attachments + body become capture items. Reuses
  the OfficeMitra email-handling pattern; no credentials stored in the frontend.
- **WhatsApp**: BSP (e.g. Meta Cloud API / Gupshup) webhook → media fetch → capture item. Phased
  last (§8, Phase 4).
- **CA doc queue**: items already in `documents_service.list_queue` can be promoted into the
  pipeline instead of only being linked to review notes.

### 4.2 Extract (AI + OCR)
New orchestrator function `extract_document()` following the exact pattern of `generate_tasks` /
`summarize_email` in [`orchestrator.py`](../../app/modules/office_ai/ai/orchestrator.py):
load a versioned prompt (`extract_invoice_v1` in `office_ai/ai/prompts/`), call
`get_ai_provider().complete(...)`, parse with `_extract_json`, record telemetry, return
`{ai_available, fields, field_confidences, prompt_version, telemetry_id, provider, model, advisory}`.

- OCR for scanned PDFs/images runs first (pluggable engine; deterministic text extraction for
  born-digital PDFs needs no model).
- The model returns **per-field confidences**, not a single self-reported overall number — this is
  what feeds the blended score and prevents a model from "claiming 99%."

### 4.3 Validate (deterministic — the real gate)
Pure, testable checks that do **not** depend on the model. A failure here forces human review
regardless of extraction confidence:
- **Arithmetic**: line totals + tax = invoice total (within rounding tolerance).
- **GSTIN**: format + checksum (reuse `gst_states.py` state resolver for the state-code prefix).
- **Duplicate**: fingerprint already seen → flag as possible duplicate, never auto-post.
- **Party resolution**: vendor/customer matched to an existing master (fuzzy, confirmed) — unknown
  party ⇒ human review.
- **GL/category mapping**: proposed expense/income account exists and maps via the COA mapping
  layer (`coa_mapping.py`); no confident mapping ⇒ human review.
- **Period lock**: target period not locked (reuse existing period-lock checks).
- **Tax regime**: composition vs regular handled correctly (no ITC legs for composition).

### 4.4 Score (blend)
```
final_confidence = min(extraction_confidence_floor, validation_factor)
```
- `extraction_confidence_floor` = the **lowest** per-field confidence among required fields.
- `validation_factor` = 1.0 only if every deterministic check passes; otherwise 0 (→ forced human
  review). This makes validation a hard gate, not a weight.

### 4.5 Route
- `final_confidence ≥ auto_threshold` (tenant-configurable, default **0.95**) **and** all validations
  pass → create the typed document as `pending_approval` (a clean, one-click-approve draft).
  - If the separate `capture_auto_post_enabled` flag is ON **and** the item is *not* bank-feed-derived
    → promote straight to `posted` through the normal posting service (still writes the same audit
    trail). Default: **OFF**.
- Otherwise → `needs_review`: the item appears in a review surface with the AI's extracted fields,
  per-field confidences, failed checks highlighted, and the source document attached. Human edits +
  confirms → normal posting.

### 4.6 Post → Match → Reconcile
- Posting always uses the existing `services/vouchers.py` / `purchase_bills.py` /
  `sales_invoices.py` entry points.
- After a bill/invoice posts, auto-suggest allocations via `allocation_service` (payment ↔ bill,
  receipt ↔ invoice).
- Bank statement lines auto-*suggest* matches via `bank_recon` — **metadata-only, explicit confirm
  by default**, per Bank Feed Policy §Policy.

---

## 5. Reuse map (what we build vs. what we call)

| Need | Reuse (existing) | Build (new) |
|---|---|---|
| AI extraction | `office_ai/ai/orchestrator.py` provider + telemetry pattern | `extract_document()` fn + `extract_invoice_v1` prompt |
| Human review routing | `business/services/approval_queue.py` (`pending_approval`) | capture-review view filter on top of it |
| Posting / journals | `services/{vouchers,purchase_bills,sales_invoices}.py` | nothing — call as-is |
| Payment matching | `allocation_service.py` | auto-suggest trigger after post |
| Bank matching | `bank_recon.py` (metadata-only) | auto-suggest trigger; confirm stays manual |
| Document intake | `office_ai/services/documents_service.py`, email pattern | source adapters + `capture_items` |
| GST/COA validation | `gst_states.py`, `coa_mapping.py`, period locks | `capture/validators.py` orchestration |
| Audit / tenancy | `core/audit/service.py`, tenant context, two-flag gate | per-stage audit events |

New module footprint (small, mirrors existing layout):
```
app/modules/business/capture/
  models.py          # CaptureItem + state machine
  service.py         # pipeline orchestration
  validators.py      # deterministic checks
  scoring.py         # blend
  sources/           # upload.py, email.py, whatsapp.py, ca_queue.py
app/modules/business/routes/capture_routes.py
app/modules/office_ai/ai/prompts/extract_invoice_v1.txt
tests/test_capture_pipeline.py
alembic/versions/<ts>_capture_items.py   # or Mongo index ensure, per existing store pattern
```

---

## 6. Data model — `CaptureItem`

| Field | Notes |
|---|---|
| `tenant_id`, `app_key`, `accounting_entity_id` | scoping, same as approval queue |
| `capture_id`, `fingerprint` | idempotent dedupe |
| `source` | `upload` \| `email` \| `whatsapp` \| `ca_queue` |
| `source_ref` | message id / upload id / ca document id |
| `document_blob_ref` | pointer into approved document retention (never raw in FE) |
| `doc_kind` | `purchase_bill` \| `sales_invoice` \| `receipt` \| `bank_line` |
| `extracted_fields`, `field_confidences` | from orchestrator |
| `validation` | list of `{check, passed, detail}` |
| `final_confidence` | blended |
| `status` | `captured → extracted → validated → drafted → posted` / `needs_review` / `rejected` / `duplicate` |
| `linked_document_id`, `journal_entry_id` | set on draft/post |
| `audit` | actor/system job id, timestamps per stage |

State machine:
`captured → extracted → validated → (drafted | needs_review | duplicate) → posted | rejected`

---

## 7. Guardrails (non-negotiable)

Derived from the [Bank Feed Policy](../operations/MITRABOOKS_BANK_FEED_POLICY.md) and the platform's
tenant-isolation posture:

1. **Two-flag gate.** Add-on is enterprise opt-in, default OFF; auto-post is a *second* flag, default
   OFF. Both per tenant.
2. **Deterministic validation is a hard gate** — AI confidence cannot override a failed check.
3. **No auto-post from bank-feed-derived rows, ever** (policy). Bank matching stays metadata-only +
   explicit confirm.
4. **All posting goes through the typed voucher + approval + reversal path.** No new GL writer.
5. **Tenant / app / entity scoping** on every record and query; dedupe fingerprint prevents
   cross-ingest contamination.
6. **Audit event per stage** (capture, extract, validate, route, post) with actor or system job id,
   source, counts, and failure detail.
7. **No credentials in the frontend**; provider/BSP tokens only in the approved backend secret store.
8. **Kill switch**: disabling the flag halts ingestion and leaves all existing documents untouched.
9. **Human-in-the-loop by default.** The default experience is "AI drafts, human approves," which is
   also the honest demo story vs. "fully autonomous."

---

## 8. Phasing

- **Phase 1 — Capture + Extract + Review (no auto-post).** Upload + email sources, `extract_document`,
  deterministic validators, drafts land in `needs_review` / `pending_approval`. Ships the whole
  value for auditability with zero posting risk.
- **Phase 2 — Confidence routing + one-click approve.** Blended score, `auto_threshold`, clean
  high-confidence drafts, allocation auto-suggest after post.
- **Phase 3 — Auto-post (flagged) + auto-match.** `capture_auto_post_enabled` promotes high-confidence
  non-bank items; bank-recon auto-suggest (confirm still manual).
- **Phase 4 — WhatsApp + continuous learning.** BSP webhook source; feed human corrections back as
  few-shot / rule hints to lift extraction confidence over time.

---

## 9. API surface (sketch, under `/business/capture/`)

- `POST /business/capture/upload` — upload a document → capture item.
- `POST /business/capture/email/webhook` / `POST /business/capture/whatsapp/webhook` — source hooks.
- `GET /business/capture/items?status=needs_review` — review queue (feeds FE view).
- `POST /business/capture/items/{id}/extract` / `.../revalidate` — re-run a stage.
- `POST /business/capture/items/{id}/draft` — materialize the typed document (pending_approval).
- `POST /business/capture/items/{id}/reject` — discard with reason (audited).
- Approval + posting reuse the existing approval-queue / posting endpoints — not duplicated here.

---

## 10. Metrics & telemetry

Reuse `office_ai/ai/metrics` + `telemetry`. Track: capture volume by source, extraction
success/latency, validation failure reasons, routing split (auto-draft vs review), auto-post rate,
**human-override rate on high-confidence drafts** (the key trust metric — if humans keep correcting
"high-confidence" items, the threshold is wrong), and time-to-post.

---

## 11. Testing strategy

- **Pure unit tests** for `validators.py` and `scoring.py` (no model, fully deterministic) — the
  most important coverage, since these are the safety gate.
- Golden-file extraction tests with a **stubbed AI provider** (the orchestrator already abstracts
  `get_ai_provider`), asserting field mapping and per-field confidence handling.
- Pipeline integration test: capture → draft → confirm → posted, asserting it lands in the existing
  approval queue and posts via the existing service (`tests/test_capture_pipeline.py`).
- Tenant-isolation + dedupe tests mirroring `test_bank_recon.py`.
- Policy regression: assert bank-feed-derived items can **never** auto-post.

---

## 12. Open questions

1. OCR engine choice (local/offline vs. cloud) given the free/local-pipeline preference and data
   residency for Indian SMBs.
2. WhatsApp BSP selection and per-tenant number provisioning cost.
3. Default `auto_threshold` — start conservative (0.95) and tune from the human-override metric.
4. Whether auto-post should ever be allowed for email/WhatsApp-captured bills, or always stop at
   one-click-approve (recommended default: stop at approve; auto-post stays a deliberate opt-in).
5. Learning loop storage: where corrections are retained for few-shot prompting without leaking
   cross-tenant data.

---

## 13. Competitive positioning recap

This add-on closes the one gap where "autonomous bookkeeper" pitches look ahead, **without**
adopting their riskiest claim (blind auto-post at a self-reported confidence). MitraBooks keeps its
real moat — India-native GST/compliance depth and being the system of record — and adds the capture
automation on top of controls competitors don't have.
