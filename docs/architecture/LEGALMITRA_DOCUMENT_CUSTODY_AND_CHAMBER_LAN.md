# LegalMitra — Document Custody Modes (Cloud vs Chamber LAN)

**Document type:** Architecture design (target)  
**Product:** LegalMitra  
**Status:** Planned (not yet implemented)  
**Version:** 1.0  
**Date:** 2026-08-03  
**Companion:**  
- Implementation plan (approval) — [`LEGALMITRA_DOCUMENT_CUSTODY_IMPLEMENTATION_PLAN.md`](LEGALMITRA_DOCUMENT_CUSTODY_IMPLEMENTATION_PLAN.md)  
- Stage 3 practice context — [`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md)  
- Stage 5 guided workflows — [`LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md`](LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md)  
- LegalMitra compliance skill / AGENTS.md LegalMitra guardrails  

This document defines **two clearly demarcated document-custody modes** so chambers with a shared office server and offices without one can both use LegalMitra safely.

**Philosophy:** LegalMitra treats documents as evidence, not as the primary source of intelligence. Intelligence is derived from structured case knowledge, selective retrieval, and human-reviewed extracts.

**Product rule:** Case papers are never public domain. Encryption in cloud storage does **not** mean “safe to treat as public.” Full document custody is always tenant-private and mode-specific. LegalMitra manages document custody according to the customer’s operating model — it is a practice intelligence platform, not a document repository.

---

## 1. Why two modes

| Reality | Need |
| --- | --- |
| Many advocate chambers already run a **LAN / shared server** used by Sr and Jr advocates | Keep full PDFs on the chamber server; LegalMitra holds practice intelligence + retrieval metadata |
| Solo / small offices often have **no chamber server** | Use LegalMitra cloud (or laptop) with minimized extracts — not unbounded full-file cloud growth |
| Both need AI assist on matters | AI must work from **case cards + selective extracts/chunks**, not by stuffing every PDF into every prompt |

LegalMitra must **not** force one storage model on all tenants.

---

## 2. Mode demarcation (non-negotiable)

Every LegalMitra tenant chooses (or is configured with) exactly one **primary document custody mode**:

| Mode key (enum) | Advocate-facing display name | Who it is for |
| --- | --- | --- |
| `cloud_minimized` | **Personal Practice** | Solo advocates, small offices, laptop-only practices (no shared chamber server) |
| `chamber_lan` | **Chamber LAN** | Chambers with shared file server and multi-advocate LAN |

Internal enum keys stay implementation-stable. UI, onboarding, and ops copy must use the **display names** (where are my files?), not engineering labels like “minimized.” Do not blur modes into “upload everything optionally.”

**Future (not implemented):** `enterprise_vault` — **Enterprise Vault** for banks, insurers, government, and corporate legal departments where originals stay in customer Azure/AWS/SharePoint/MinIO and LegalMitra holds metadata/AI/workflow only. Do not expose in UI until a later phase.

```text
                    ┌──────────────────────────────┐
                    │  LegalMitra cloud tenant     │
                    │  clients · matters · briefs  │
                    │  Morning Brief · workflows   │
                    │  fees · case card · metadata │
                    └──────────────┬───────────────┘
                                   │
           ┌───────────────────────┴───────────────────────┐
           │                                               │
           ▼                                               ▼
 ┌─────────────────────┐                     ┌─────────────────────────┐
 │ MODE A              │                     │ MODE B                  │
 │ Personal Practice   │                     │ Chamber LAN             │
 │ (cloud_minimized)   │                     │ (chamber_lan)           │
 │                     │                     │                         │
 │ Full files: device  │                     │ Full files: chamber     │
 │ or opt-in private   │                     │ LAN/server ONLY         │
 │ store               │                     │                         │
 │ Prefer: case card + │                     │ SanMitra Chamber        │
 │ extracts + chunks   │                     │ Connector pushes only   │
 │ Retention tiers     │                     │ metadata / extracts     │
 └─────────────────────┘                     └─────────────────────────┘
```

**Intelligence stack (both modes):** Matter → Case Card → Matter Snapshot (planned) → Extracts → AI assist. The PDF is evidence; structured knowledge is the centre.

---

## 3. Current state vs target vs gap

| Area | Current state | Target | Gap |
| --- | --- | --- | --- |
| Matter document API | Metadata register (`filename`, `doc_type`, `notes`, `storage_ref`) | Mode-aware custody + register | No mode flag; no binary ingest pipeline; no chamber connector |
| Stage 5 research/draft | Uses matter fields + doc **filenames** as weak signals | Grounds on case card + approved extracts/chunks per mode | No PDF/text extraction into Stage 5; no LAN connector |
| Storage minimization | Not designed | Case card + chunks + retention; originals cold or local | No retention tiers; no dedupe hashes; no extract pipeline |
| Chamber LAN | Not implemented | Connector on office server; Sr/Jr ACL | Entire Mode B stack |
| Solo / no server | Tracker + APIs; console attach metadata | Mode A cloud minimized path | UX for attach/register; extract/chunk; retention policy UI |

**Current state must not be described as if Mode B or full Mode A ingest already ships.**

---

## 4. Mode A — `cloud_minimized` (no chamber server)

### 4.1 Intent

**Personal Practice** for offices **without** a shared server. Advocates keep using LegalMitra in the browser. Full papers may live on the advocate’s laptop or, if the tenant opts in, in **private** tenant object storage — never public.

### 4.2 What LegalMitra stores (preferred)

| Store | Content |
| --- | --- |
| Matter **case card** | Parties, case number, court, jurisdiction, next dates, issues, opposite party |
| Document register | Filename, type, hash, optional `storage_ref`, notes |
| Extracts / chunks | Short structured facts + retrieval chunks (not entire PDF in every prompt) |
| Optional original | Only if tenant opts into private cloud object storage |

### 4.3 Minimization rules (Mode A)

1. Prefer **extract + case card** over keeping hot full-text of every upload.  
2. **Chunk + retrieve** only relevant passages for a question.  
3. **Deduplicate** by content hash.  
4. **Retention tiers:** hot (active matter card/chunks) → warm (extracts) → cold (original if any) → purge/archive per tenant policy.  
5. Do not retain model chat as the system of record; reusable knowledge lives in the case card / extracts.  
6. Do not send confidential documents to external AI providers unless tenant policy and user authorization allow it.

### 4.4 When Mode A is the default

- Solo practice / no LAN server  
- Advocate works primarily from one laptop  
- Chamber declines any office-server connector  

---

## 5. Mode B — `chamber_lan` (office server available)

### 5.1 Intent

**Chamber LAN** for chambers that already share a **file server / NAS / Windows Server** among Sr and Jr advocates. Full case papers stay on that server. LegalMitra cloud holds practice workflows and **retrieval metadata/extracts only**.

### 5.2 Topology

```text
Chamber LAN
  Sr PC ─┐
  Jr PC ─┼──▶ Chamber Document Server (matter folders + ACLs)
  Clerk ─┘         │
                   │ SanMitra Chamber Connector (separate package / future repo)
                   │  - watches folders
                   │  - fingerprints + classifies + extracts
                   │  - optional Local AI on LAN (planned)
                   │  - pushes metadata/extracts only
                   ▼
            LegalMitra cloud (tenant = chamber)
```

**Connector packaging (target):** Treat the connector as **SanMitra Chamber Connector** — reusable infrastructure (LegalMitra first; later MitraBooks / other products if approved). Prefer a separate repository when implementation starts (P3), not a LegalMitra-only embed.

### 5.3 What stays where

| Location | Holds |
| --- | --- |
| Chamber server | Full court orders, notices, pleadings, evidence, annexures |
| Chamber Connector | Local index, extract jobs, hash index (on-prem) |
| LegalMitra cloud | Clients, matters, hearings, Morning Brief, workflows, fees, case card, doc metadata, approved extracts/chunks |

### 5.4 Sr / Jr collaboration

- **Server ACLs:** folder permissions by matter/team (existing chamber IT practice).  
- **LegalMitra RBAC:** same tenant; roles limit which matters appear in Tracker/workflows.  
- Jr advocates use the same chamber document root; they do not each upload duplicate full trees to the cloud.

### 5.5 Minimization rules (Mode B)

1. **Default: do not upload full PDFs to LegalMitra cloud.**  
2. Connector sends **case card updates + metadata + selective extracts/chunks** only.  
3. Deep “read this order” may resolve against the **LAN connector** when the advocate is in office.  
4. Optional encrypted cloud backup of originals is **opt-in**, never default, never public.  
5. Same provider/confidentiality rules as Mode A for any text that does leave the LAN.

### 5.6 When Mode B is offered

- Tenant confirms shared chamber server / LAN  
- IT can run a small Connector service (or approved appliance)  
- Multi-advocate firm wants one document custody point  

---

## 6. Shared LegalMitra layer (both modes)

Regardless of mode, LegalMitra cloud remains the system of record for:

- Clients and matters (Stage 3)  
- Morning Brief / alerts (Stage 4)  
- Guided Prepare Matter Response (Stage 5) — human-gated, advisory  
- Practice fees (Stage 6)  
- Tenant isolation, `app_key=legalmitra`, audit  

AI outputs remain **advisory / draft** until human review. No auto-file or auto-send.

---

## 7. Configuration sketch (target)

Illustrative tenant settings (not yet implemented):

```text
LEGALMITRA_DOC_CUSTODY_MODE=cloud_minimized | chamber_lan
LEGALMITRA_DOC_CLOUD_ORIGINALS_OPT_IN=false   # Mode A only; default off
LEGALMITRA_CHAMBER_CONNECTOR_ENABLED=false  # Mode B
LEGALMITRA_EXTRACT_RETENTION_DAYS=...       # tenant policy
```

Frontend onboarding copy must ask:

> “Does this chamber use a shared office file server for case papers?”  
> → Yes → **Chamber LAN** guidance  
> → No → **Personal Practice** guidance  

Badge copy examples: `Document custody: Personal Practice` / `Document custody: Chamber LAN`.  

---

## 8. Implementation sequence

| Phase | Scope | Modes |
| --- | --- | --- |
| **P0** | Architecture + plan; tenant custody settings; mode badge; audit | Both |
| **P1** | Tracker document register; case-card completeness; fingerprint fields on register | A (+ B register mirror) |
| **P2** | Classification → extract/chunk; Matter Snapshot; retention/dedupe; Stage 5 grounding | A first |
| **P3** | SanMitra Chamber Connector MVP (separate package); metadata/extracts push | B |
| **P4** | Deep retrieve; opt-in backup; optional Local AI on LAN | B (+ A opt-in) |

Do not start P3/P4 until P0 mode demarcation is product-approved. `enterprise_vault` remains deferred.

---

## 9. Planned enrichments (later phases — design now)

| Concept | Intent | Earliest phase |
| --- | --- | --- |
| **Matter Snapshot** | Living structured summary (facts, issues, timeline, deadlines, open questions, research, confidence) as primary Stage 5 context | P2 |
| **Document fingerprint** | Hash, version, pages, language, OCR status, classification, extract status | P1 fields / P2 pipeline |
| **Document classification** | Court order, notice, affidavit, petition, evidence, contract, tax notice, invoice, identity, board resolution — drives extract strategy | P2 |
| **Local AI (Mode B)** | Optional Ollama/Qwen/Llama on chamber server so sensitive text never leaves the LAN | P4 |
| **Enterprise Vault** | Customer cloud vault; LegalMitra = metadata/AI/workflow only | Future mode key |

## 10. Non-goals

- Making case documents public or SEO-visible  
- Forcing all chambers onto LAN connectors  
- Forcing all solo offices to buy a server  
- Storing full PDF bodies inside LLM provider context by default  
- Merging LegalMitra document custody into MitraBooks ERP  
- Replacing chamber IT backup policies  
- Shipping Enterprise Vault or Local AI in P0–P2  

---

## 11. Security and privacy checklist

- [ ] Tenant-scoped reads/writes for all metadata and extracts  
- [ ] Mode B never defaults to uploading full originals to cloud  
- [ ] Mode A cloud originals only behind explicit opt-in  
- [ ] External provider calls gated by tenant policy + user action  
- [ ] Retention/purge documented per mode  
- [ ] Audit: who registered/extracted/synced which document  
- [ ] Clear in-product label of active custody mode  

---

## 12. Decision summary

| Question | Answer |
| --- | --- |
| Chamber has shared server/LAN? | **Chamber LAN** (`chamber_lan`) |
| No server / solo laptop? | **Personal Practice** (`cloud_minimized`) |
| Where do full case papers live by default? | Chamber LAN: chamber server. Personal Practice: device or opt-in private store |
| What does AI need first? | Case card → Matter Snapshot → selective extracts — not every byte of every upload |
| Are papers public if encrypted in cloud? | **No** — still private tenant data; Chamber LAN avoids that custody when possible |

---

## 13. Next engineering actions

1. ~~Product sign-off on mode naming and onboarding~~ (approved with Personal Practice display name).  
2. **P0 implement:** custody settings on Legal practice tenant scope + Tracker badge + audit.  
3. P1 Tracker document-register + fingerprint fields.  
4. Spec **SanMitra Chamber Connector** as a separate package/repo (Windows service first).  

Operators must distinguish: **P0 settings/badge may ship while extract pipeline and Connector remain planned.**
