# LegalMitra — Document Custody Modes (Cloud vs Chamber LAN)

**Document type:** Architecture design (target)  
**Product:** LegalMitra  
**Status:** Planned (not yet implemented)  
**Version:** 1.0  
**Date:** 2026-08-03  
**Companion:**  
- Stage 3 practice context — [`LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md`](LEGALMITRA_STAGE3_MATTER_CLIENT_INTELLIGENCE.md)  
- Stage 5 guided workflows — [`LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md`](LEGALMITRA_STAGE5_AGENTIC_WORKFLOWS.md)  
- LegalMitra compliance skill / AGENTS.md LegalMitra guardrails  

This document defines **two clearly demarcated document-custody modes** so chambers with a shared office server and offices without one can both use LegalMitra safely.

**Product rule:** Case papers are never public domain. Encryption in cloud storage does **not** mean “safe to treat as public.” Full document custody is always tenant-private and mode-specific.

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

| Mode key | Display name | Who it is for |
| --- | --- | --- |
| `cloud_minimized` | **Cloud minimized (no chamber server)** | Solo advocates, small offices, laptop-only practices |
| `chamber_lan` | **Chamber LAN / office server** | Chambers with shared file server and multi-advocate LAN |

UI, onboarding, and ops docs must label these modes explicitly. Do not blur them into “upload everything optionally.”

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
 │ cloud_minimized     │                     │ chamber_lan             │
 │                     │                     │                         │
 │ Full files: optional│                     │ Full files: chamber     │
 │ object store OR     │                     │ LAN/server ONLY         │
 │ advocate device     │                     │                         │
 │ Prefer: extracts +  │                     │ Connector pushes only   │
 │ case card + chunks  │                     │ metadata / extracts     │
 │ Retention tiers     │                     │ to cloud tenant         │
 └─────────────────────┘                     └─────────────────────────┘
```

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

Offices **without** a shared server keep using LegalMitra in the browser. Full papers may live on the advocate’s laptop or, if the tenant opts in, in **private** tenant object storage — never public.

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

Chambers that already share a **file server / NAS / Windows Server** among Sr and Jr advocates keep **full case papers on that server**. LegalMitra cloud holds practice workflows and **retrieval metadata/extracts only**.

### 5.2 Topology

```text
Chamber LAN
  Sr PC ─┐
  Jr PC ─┼──▶ Chamber Document Server (matter folders + ACLs)
  Clerk ─┘         │
                   │ Chamber Connector (local service)
                   │  - watches folders
                   │  - extracts case-card fields + chunks
                   │  - pushes metadata/extracts only
                   ▼
            LegalMitra cloud (tenant = chamber)
```

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
> → Yes → Mode B guidance  
> → No → Mode A guidance  

---

## 8. Implementation sequence

| Phase | Scope | Modes |
| --- | --- | --- |
| **P0** | This architecture doc; tenant mode enum design; UI copy demarcation | Both |
| **P1** | Tracker “document register” UX (metadata); case-card fields completeness | A (and B register mirroring) |
| **P2** | Extract pipeline → case card + chunks; retention/dedupe | A first |
| **P3** | Chamber Connector MVP (folder watch → metadata/extracts push) | B |
| **P4** | In-office deep retrieval via connector; optional opt-in cloud original backup | B (+ A opt-in) |

Do not start P3/P4 until P0 mode demarcation is product-approved.

---

## 9. Non-goals

- Making case documents public or SEO-visible  
- Forcing all chambers onto LAN connectors  
- Forcing all solo offices to buy a server  
- Storing full PDF bodies inside LLM provider context by default  
- Merging LegalMitra document custody into MitraBooks ERP  
- Replacing chamber IT backup policies  

---

## 10. Security and privacy checklist

- [ ] Tenant-scoped reads/writes for all metadata and extracts  
- [ ] Mode B never defaults to uploading full originals to cloud  
- [ ] Mode A cloud originals only behind explicit opt-in  
- [ ] External provider calls gated by tenant policy + user action  
- [ ] Retention/purge documented per mode  
- [ ] Audit: who registered/extracted/synced which document  
- [ ] Clear in-product label of active custody mode  

---

## 11. Decision summary

| Question | Answer |
| --- | --- |
| Chamber has shared server/LAN? | Use **Mode B — chamber_lan** |
| No server / solo laptop? | Use **Mode A — cloud_minimized** |
| Where do full case papers live by default? | Mode B: chamber server. Mode A: device or opt-in private store |
| What does AI need first? | Case card + selective extracts — not every byte of every upload |
| Are papers public if encrypted in cloud? | **No** — still private tenant data; Mode B avoids that custody when possible |

---

## 12. Next engineering actions

1. Product sign-off on Mode A / Mode B naming and onboarding question.  
2. Add `doc_custody_mode` to tenant configuration design (schema + module registry notes).  
3. P1 Tracker document-register panel for Mode A (and Mode B status “linked from chamber server”).  
4. Spec Chamber Connector package (Windows service first — common in Indian chambers).  

Until those land, operators and docs must keep saying: **planned dual-mode custody — not yet implemented.**
