# Indian CA Practice Software — Competitive Positioning Note

Date: 2026-09-13  
Status: **Research / positioning** (not a feature commitment)  
Audience: product, engineering, CA demos  

Source input: 2025 market research summary covering Marg ERP CA, Tally Prime, Zoho Books, and ClearTax Pro. Competitor claims below are **market messaging**; they are not independently verified product certifications and must not be copied into SanMitra release notes as facts about those products.

## Purpose

Map common Indian CA-software lanes to SanMitra’s **current** MitraBooks + OfficeMitra split, so demos and roadmaps stay honest:

- What we **are** today
- What we **target** next
- What stays **deferred / out of scope** until ADRs and compliance signoff say otherwise

## Lane map (competitors → SanMitra)

| Competitor (lane) | Typical buyer need | SanMitra response |
| --- | --- | --- |
| **Marg ERP CA** — CA practice shell (multi-client, staff access, voucher/internal review, reports) | Firm runs many client books + junior → partner review | Closest peer for **OfficeMitra** Review / working papers / review notes / staff Documents — not a new Mitra brand |
| **Tally Prime / Zoho Books** — client accounting + compliance tooling | Books of account, GST/TDS ops, remote access | **MitraBooks** Unified ERP (and companion Mandir/Gruha books where enabled). Compete on multi-tenant books and ERP depth |
| **ClearTax Pro** — tax compliance portal filing | GST / ITR / TDS filed to government systems | **Do not chase as core product** until CA filing signoff + a superseding filing ADR. Stay preparation / reporting |

### Category split (from the research)

| Category | Examples in market | SanMitra today |
| --- | --- | --- |
| Practice management | Clients, tasks, deadlines, team workflow, audit docs | OfficeMitra tasks + Review notes + Documents (staff); practice depth still growing |
| Compliance preparation | GST/TDS/IT returns, ITC, certificates | MitraBooks GST/TDS **preparation** reports and settlement **books** postings |
| Compliance filing | Direct GSTN / IT portal submit | **Not enabled** — see [`MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md`](../operations/MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md) |
| Statutory audit tools | Checklists, working papers | OfficeMitra working papers + Review scan (ADR-015); not a full statutory-audit suite |

## Current state (what exists now)

### MitraBooks (client books)

- Shared double-entry engine; parties, vouchers, invoices/bills/notes, inventory/banking slices, GST/TDS **preparation** surfaces, settlement as **books** set-off (not GSTN payment).
- CA multi-client practice: distinct client books (`client-*` accounting entities), staff document queue, governed exports (incl. Tally XML **ledger-master PoC**).
- Hosted Phase 3 destructive demo mutation reconfirmed 2026-09-13 on `demo-mitrabooks-business`.

### OfficeMitra (CA practice layer — thin orchestration)

- Review / working papers / review notes behind `office_ai.review*` (**default off**); smoke PASS 2026-09-13 on `demo-mfg-mis` only ([ADR-015](../adr/ADR-015-officemitra-review-workspaces.md)).
- Staff Documents + missing-doc requests behind `office_ai.documents*` (**default off**; no client portal) ([ADR-016](../adr/ADR-016-officemitra-documents-package.md), [ADR-017](../adr/ADR-017-officemitra-missing-document-requests.md)).
- CA Analysis Pack / live MitraBooks MIS reads behind `office_ai.mis*` (**default off**); Zoho/Tally ingest still deferred ([ADR-014](../adr/ADR-014-officemitra-ca-analysis-pack.md)).

### Explicit non-claims (current)

Do **not** tell tenants:

- “MitraBooks / OfficeMitra files your GST return.”
- “IRN is generated automatically.”
- “TDS is deposited / 26Q–27EQ is filed from SanMitra.”
- “We replace ClearTax / Marg / Tally end-to-end.”

Allowed (when accurate for the tenant’s enabled modules):

- “MitraBooks prepares GSTR / TDS registers from posted books; download JSON and review before any portal upload.”
- “OfficeMitra Review runs engagement scan, working papers, and notes without posting to the live ledger.”
- “GST settlement in MitraBooks sets off ITC in the books; you still pay GST on the portal.”

## Target state (near-term product intent)

1. **One pitch:** MitraBooks = client books; OfficeMitra = CA practice layer (review, papers, notes, staff docs, MIS) — cloud SaaS, not Marg-style one-time desktop.
2. **Practice depth:** staff assignment per client book, clearer partner/manager/staff access, pricing/client caps where productized.
3. **Compliance honesty:** human CA signature on preparation readiness ([`MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md`](../operations/MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md)); UI stays “Download GSTN JSON,” never “File return.”
4. **Interop:** deepen Tally/Zoho **ingest or export** only behind Accepted ADRs (ADR-014 Path B/C still deferred; voucher-level Tally XML still a MitraBooks residual).

## Gap (what must be built or signed before the target is real)

| Gap | Why it matters vs market | Status |
| --- | --- | --- |
| Human CA / filing **preparation** signoff | Competitors market “filing”; we must not over-claim | Checklist ready; signature **open** |
| CA staff assignment per book + pricing caps | Marg/Zoho multi-company practice expectation | Pending (known MitraBooks practice residual) |
| Opening balance / year-end operator signoff | Practice year-close credibility | Local/demo covered; production operator signoff open |
| Voucher-level Tally XML + real import validation | Data exchange vs Tally-dominated market | Ledger-master PoC only |
| Companion write-back (journals/GST from OfficeMitra) | “Practice drives books” workflows | [ADR-010](../adr/ADR-010-officemitra-companion-writeback.md) **Proposed** — not Accepted |

## Deferred / non-goals (this note)

- Live GSTN / GSP filing, ARN/amendment workflows, live IRP / e-way APIs.
- Income-tax return product (ClearTax lane).
- Desktop Electron / one-time ₹9k lifetime AMC commercial model (legacy desktop plans are not the unified SaaS target — see [`MITRABOOKS_ERP_GAP_MATRIX.md`](MITRABOOKS_ERP_GAP_MATRIX.md)).
- New Mitra product brands (no PracticeMitra / AuditMitra). Review packages stay under OfficeMitra ([ADR-015](../adr/ADR-015-officemitra-review-workspaces.md)).
- InvestMitra in unified CA practice scope.

## Suggested sequencing (after this note)

1. Demo the **Review trio** (already smoke-PASS on `demo-mfg-mis`) as the Marg-comparable wedge.
2. Keep GST/TDS **preparation-only**; obtain CA checklist signature when ready.
3. Close **staff assignment per book + pricing caps** before promising “full CA firm multi-client like Marg.”
4. Only after compliance + ADR: consider live filing or companion write-back — never by marketing alone.

## One-line positioning

> MitraBooks runs the client’s books; OfficeMitra runs the CA’s review and working papers — without pretending we file GST for you.

## Cross-references

- [`MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md`](../operations/MITRABOOKS_GST_TDS_COMPLIANCE_REVIEW.md)
- [`MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md`](../operations/MITRABOOKS_GST_TDS_CA_FILING_SIGNOFF_CHECKLIST.md)
- [`OFFICEMITRA_REVIEW_WORKSPACES.md`](OFFICEMITRA_REVIEW_WORKSPACES.md)
- [`CURRENT_VS_TARGET.md`](../architecture/CURRENT_VS_TARGET.md)
- [`MITRABOOKS_ERP_GAP_MATRIX.md`](MITRABOOKS_ERP_GAP_MATRIX.md)
- ADR-010, ADR-014, ADR-015, ADR-016, ADR-017
