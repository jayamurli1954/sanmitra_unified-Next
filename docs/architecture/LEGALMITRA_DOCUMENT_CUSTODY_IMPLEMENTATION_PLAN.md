# LegalMitra — Document Custody Modes Implementation Plan

**Document type:** Implementation plan (for product approval)  
**Product:** LegalMitra  
**Status:** P0 implemented locally (awaiting commit/PR); P1–P4 not started  
**Version:** 1.2  
**Date:** 2026-08-03  
**Architecture source:** [`LEGALMITRA_DOCUMENT_CUSTODY_AND_CHAMBER_LAN.md`](LEGALMITRA_DOCUMENT_CUSTODY_AND_CHAMBER_LAN.md)

---

## 0. Approval decisions (locked)

| # | Decision | Locked value |
| --- | --- | --- |
| D1 | Enum keys | `cloud_minimized` \| `chamber_lan` (`enterprise_vault` future only) |
| D1b | UI display names | **Personal Practice** / **Chamber LAN** (not “cloud minimized”) |
| D2 | Onboarding | “Does this chamber use a shared office file server for case papers?” |
| D3 | Default | Personal Practice (`cloud_minimized`) |
| D4 | Ship order | P0→P1→P2 then P3→P4 |
| D5–D6 | Originals | Opt-in Mode A only; Mode B never defaults full PDFs to cloud |
| D7 | First code | P0 settings + badge + audit |
| D8 | P1 case card | `case_number` + `issues` |
| D9 | Connector | Package as **SanMitra Chamber Connector** (prefer separate repo at P3) |
| D10 | Later enrichments | Matter Snapshot, fingerprint, classification, Local AI (Mode B), Enterprise Vault — not P0 |

**Philosophy:** LegalMitra treats documents as evidence, not as the primary source of intelligence. Intelligence is derived from structured case knowledge, selective retrieval, and human-reviewed extracts.

---

## 1. Current state (baseline)

| Capability | Exists today? | Notes |
| --- | --- | --- |
| Matter document register API | Yes | `POST/GET /api/v1/legal/matters/{id}/documents` — metadata only (`filename`, `doc_type`, `notes`, `storage_ref`) |
| Binary upload for matter papers | No | No matter-linked object store pipeline |
| Content hash / dedupe | No | Not on `legal_matter_documents` |
| Extract / chunk for matter papers | No | Stage 5 / briefs use matter fields + **filenames** only |
| Tenant `doc_custody_mode` | No | Tenant schema has org type / modules / plan only |
| Tracker document-register UI | No | Case Master is live-read for matters; attach is console/API only |
| Chamber Connector | No | Entire Mode B stack missing |
| Separate RAG ingest | Yes | Statute/knowledge corpus — **not** matter case-paper custody |

**Important:** Do not describe current product as if Mode A ingest or Mode B LAN custody already ships.

---

## 2. Target principle (both modes)

```text
LegalMitra cloud = practice intelligence
  clients · matters · case card · briefs · workflows · fees · metadata · selective extracts

Full case papers = mode-specific custody
  Mode A: advocate device OR optional private cloud originals (opt-in, default off)
  Mode B: chamber LAN/server ONLY (default); cloud never gets full PDFs by default
```

AI / Stage 5 must ground on **case card + approved extracts/chunks**, not full PDF stuffing into every prompt. Outputs stay **advisory / human-gated**.

---

## 3. Mode demarcation (product UX — non-negotiable)

| Surface | Personal Practice (`cloud_minimized`) | Chamber LAN (`chamber_lan`) |
| --- | --- | --- |
| Settings badge | “Document custody: Personal Practice” | “Document custody: Chamber LAN” |
| Document panel title | “Document register” | “Document register (linked from chamber server)” |
| Empty state | “Register papers here. Prefer extracts over keeping every full file hot in cloud.” | “Full papers stay on your chamber server. LegalMitra holds metadata and extracts only.” |
| Upload control | Optional register + (later) extract; originals only if opt-in | No full-PDF cloud upload by default; sync status from Connector |
| Mode switch | Explicit admin action + audit; warn about custody change | Same |

Modes must not blur into “upload everything optionally.”

---

## 4. Phased delivery

### P0 — Demarcation + tenant config design (both modes)

**Goal:** Product-visible mode choice and durable tenant setting. No Connector. No binary ingest yet.

| # | Work item | Deliverable |
| --- | --- | --- |
| P0.1 | Architecture doc (done) | `LEGALMITRA_DOCUMENT_CUSTODY_AND_CHAMBER_LAN.md` |
| P0.2 | This implementation plan | This file — approval gate |
| P0.3 | Tenant field design | `doc_custody_mode: cloud_minimized \| chamber_lan` on Legal tenants (default `cloud_minimized`) |
| P0.4 | Related flags (design + schema stubs) | `doc_cloud_originals_opt_in` (bool, default false, Mode A only); `chamber_connector_enabled` (bool, default false, Mode B only); `extract_retention_days` (int, tenant policy) |
| P0.5 | Read API | Practice/settings endpoint returns active custody mode + labels for UI badge |
| P0.6 | Admin write path | Authenticated tenant-admin update of custody mode with audit event |
| P0.7 | Frontend demarcation | Tracker/settings: mode badge + onboarding one-question copy (even before full register UX) |
| P0.8 | Tests | Tenant isolation; default Mode A; Mode B cannot enable cloud-originals opt-in; invalid mode rejected |

**Acceptance (P0):**

- [ ] New Legal demo/tenant resolves Mode A by default  
- [ ] UI shows a clear custody-mode label  
- [ ] Docs/ops language: Mode A vs Mode B never collapsed  
- [ ] No full-file upload path introduced yet  

**Exit:** Product sign-off on naming + onboarding question + default Mode A.

---

### P1 — Document register UX + case-card completeness (Mode A primary; Mode B register mirror)

**Goal:** Advocates can register papers against a live matter in Tracker without console hacks. Still metadata-first.

| # | Work item | Deliverable |
| --- | --- | --- |
| P1.1 | Tracker panel | Document register under Case Master / `#tracker-detail` — list + add (filename, doc_type, notes, optional `storage_ref`) |
| P1.2 | Wire live APIs | Use existing `POST/GET .../matters/{id}/documents` when `matter_id` selected |
| P1.3 | Mode-aware empty states | Mode A vs Mode B copy from §3 |
| P1.4 | Case-card gaps | Add/extend matter fields needed for AI grounding: e.g. `case_number` (court cause title/number), `issues` (short list/text) — keep jurisdiction/court/dates/opposite_party |
| P1.5 | Register enrichment | Persist `content_hash` when known; `custody_source` = `manual_register` \| `chamber_sync` (for later Mode B) |
| P1.6 | Timeline / audit | Keep existing attach timeline + audit; surface last register actor in UI |
| P1.7 | Tests + smoke | Attach/list tenant isolation; Tracker smoke for register panel |

**Acceptance (P1):**

- [ ] From Tracker, advocate registers a document against a live matter and sees it listed  
- [ ] Mode badge remains visible; Mode B shows “linked from chamber server” even if Connector not yet live  
- [ ] Stage 5 “missing documents” reflects register (same collection as today)  
- [ ] Still no requirement to upload full PDF binaries  

**Deferred in P1:** PDF binary upload, OCR, chunk retrieve, Connector.

---

### P2 — Extract pipeline + retention (Mode A first)

**Goal:** Solo / no-server offices get minimized cloud intelligence from papers without unbounded hot full-text.

| # | Work item | Deliverable |
| --- | --- | --- |
| P2.1 | Ingest path (Mode A) | Optional upload **or** paste/extract text → create extract + chunks linked to `matter_id` + `document_id` |
| P2.2 | Case-card updater | Human-gated or suggest-and-apply: fill/update case card fields from extract (never silent overwrite of advocate-edited fields without review) |
| P2.3 | Chunk store | Matter-scoped chunks (separate from statute RAG corpus, or clearly tagged `source_kind=matter_paper`) |
| P2.4 | Stage 5 / brief grounding | Research/draft adapters pull approved extracts/chunks, not filenames alone |
| P2.5 | Dedupe | Hash-based skip of duplicate ingest |
| P2.6 | Retention tiers | Hot (case card + active chunks) → warm (extracts) → cold (optional original if opt-in) → purge per `extract_retention_days` |
| P2.7 | Provider gate | External AI only with tenant policy + explicit user action; fail closed |
| P2.8 | Opt-in originals | `doc_cloud_originals_opt_in` required before storing full binary in private object store; default off |
| P2.9 | Tests | Tenant isolation; Mode B tenant rejects Mode A full-original upload by default; retention job dry-run; Stage 5 uses chunks when present |

**Acceptance (P2):**

- [ ] Mode A matter can produce case-card suggestions + chunks without keeping full PDF hot by default  
- [ ] Stage 5 draft/research cites matter extracts with attribution/source document id  
- [ ] Mode B tenants still cannot accidentally become “upload all PDFs to cloud”  

**Deferred in P2:** Chamber Connector, in-office deep retrieval.

---

### P3 — Chamber Connector MVP (Mode B)

**Goal:** Chambers with LAN keep full papers on office server; LegalMitra receives metadata/extracts only.

| # | Work item | Deliverable |
| --- | --- | --- |
| P3.1 | Connector package spec | Windows service first (common in Indian chambers): install, auth (tenant + connector token), folder map |
| P3.2 | Folder watch | Matter folder → file create/update → hash → extract job on-prem |
| P3.3 | Push API | Authenticated endpoint(s): upsert document register + extracts/chunks; **reject full PDF body by default** |
| P3.4 | Matter linking | Mapping rules: folder name / matter_number / admin map UI |
| P3.5 | UI sync status | Tracker shows last sync time, file count, connector health |
| P3.6 | RBAC | Connector token scoped to tenant; Sr/Jr still use LegalMitra RBAC for which matters appear |
| P3.7 | Ops runbook | Install, rotate token, offline behavior, what never leaves LAN |
| P3.8 | Tests | Push rejects oversized/binary default; tenant isolation; Mode A tenants cannot enable connector without mode switch |

**Acceptance (P3):**

- [ ] Demo Mode B: file appears on chamber folder → register + extract appear in cloud; no full PDF stored in cloud by default  
- [ ] In-product Mode B label + sync status accurate  
- [ ] Architecture non-goals respected  

**Prerequisite:** P0 mode demarcation approved and Mode B set on tenant.

---

### P4 — Deep retrieval + optional backups

**Goal:** In-office “open this order” and carefully gated backups.

| # | Work item | Modes |
| --- | --- | --- |
| P4.1 | Deep retrieve via Connector when advocate on LAN | B |
| P4.2 | Offline / away-from-office behavior (extracts only; clear UX) | B |
| P4.3 | Optional encrypted cloud backup of originals (opt-in, never default, never public) | B (+ A opt-in already in P2) |
| P4.4 | Retention/purge + audit completeness for both modes | Both |

**Acceptance (P4):** Security checklist in architecture §10 fully checked for shipping tenants.

---

## 5. Suggested engineering sequence (after approval)

```text
Approve this plan
    │
    ▼
P0  tenant mode + UI badge + audit          ← first code PR
    │
    ▼
P1  Tracker document register + case card   ← Mode A usable without server
    │
    ▼
P2  extract/chunk/retention + Stage 5 ground ← Mode A “minimized cloud” real
    │
    ▼
P3  Chamber Connector MVP                   ← Mode B for LAN chambers
    │
    ▼
P4  deep retrieve + opt-in backup
```

**Do not start P3/P4 until P0 naming/default/onboarding are product-approved.**

---

## 6. Concrete first PR (after approval) — P0 scope only

Proposed first implementation PR (single feature batch):

1. Tenant fields: `doc_custody_mode`, `doc_cloud_originals_opt_in`, `chamber_connector_enabled`, `extract_retention_days` (sensible defaults).  
2. Admin GET/PATCH under Legal practice settings (tenant-scoped, RBAC).  
3. Tracker badge + settings/onboarding copy for Mode A vs Mode B.  
4. Unit/API tests for defaults and mode validation.  
5. Cross-link architecture + this plan in Stage 3 companion notes if needed (one-line).  

**Out of first PR:** binary upload, Connector, extract pipeline, Stage 5 grounding changes.

---

## 7. Risks and guardrails

| Risk | Mitigation |
| --- | --- |
| Chambers confuse Mode A upload with “safe public cloud” | Explicit Mode A copy: still private; encryption ≠ public |
| Mode B accidental full-PDF API | Reject binary body by default on connector push |
| Mixing statute RAG with matter papers | Tag `source_kind`; never pollute citation corpus with confidential filings |
| Provider leakage | Tenant policy + user authorization; fail closed |
| Scope creep into MitraBooks | Non-goal — LegalMitra-only custody |

Critical labels if violated: `[CRITICAL-LEGAL]`, `[CRITICAL-TENANCY]`, `[CRITICAL-SECURITY]`.

---

## 8. Test expectations by phase

| Phase | Mandatory tests |
| --- | --- |
| P0 | Mode default; invalid mode; tenant isolation on settings read/write; Mode B + cloud-originals opt-in rejected |
| P1 | Document register attach/list tenant-scoped; Tracker smoke |
| P2 | Extract/chunk tenant-scoped; Stage 5 uses chunks; retention dry-run; provider gate |
| P3 | Connector auth; push rejects full original by default; Mode A cannot enable connector without switch |
| P4 | Deep retrieve ACL; opt-in backup audit |

Preflight before push: `python scripts/preflight.py` (+ `--frontend` when Tracker changes).

---

## 9. Deferred / out of scope for this plan

- Public or SEO-visible case documents  
- Forcing all chambers onto Connector  
- Forcing solo offices to buy a server  
- Full PDF bodies in LLM context by default  
- Merging custody into MitraBooks ERP  
- Replacing chamber IT backup products  
- Mobile-first Connector (Windows service first)  
- Automatic mode detection without human confirmation  

---

## 10. Decision checklist (sign-off)

| # | Decision | Proposed | Approve? |
| --- | --- | --- | --- |
| D1 | Mode keys / display names | `cloud_minimized` / `chamber_lan` as in architecture | ☐ |
| D2 | Onboarding question | Shared office file server? Yes→B No→A | ☐ |
| D3 | Default for new Legal tenants | Mode A | ☐ |
| D4 | Ship order | P0→P1→P2 then P3→P4 | ☐ |
| D5 | Mode A cloud originals | Opt-in only, default off | ☐ |
| D6 | Mode B full PDFs in cloud | Never default; reject on Connector push | ☐ |
| D7 | First code PR | P0 only (settings + badge + tests) | ☐ |
| D8 | Case-card fields in P1 | Add `case_number` + `issues` (or amend list) | ☐ |

**Platform owner:** _________________ **Date:** _________

---

## 11. After approval — immediate next step

On explicit “approved, implement P0”:

1. Implement P0 tenant settings + Tracker mode badge.  
2. Open PR with AGENTS checklist (tenant isolation, Legal confidentiality, current vs target language).  
3. Hold P1 until P0 merged and mode labels verified on staging demo tenant.
