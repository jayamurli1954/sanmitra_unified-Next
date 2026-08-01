# LegalMitra Criminal Code Crosswalk Tool

## Current state

LegalMitra has a **deterministic** old↔new criminal / evidence code crosswalk so research
answers do not invent successor section numbers.

| Piece | Location |
| --- | --- |
| Combined registry | `data/legal_seed/india_criminal_code_crosswalk_v1.json` (**v1.3**, ~1200+ pairs) |
| IPC↔BNS extract | `data/legal_seed/india_bns_ipc_comparative_v1.json` |
| CrPC↔BNSS extract | `data/legal_seed/india_bnss_crpc_comparative_v1.json` |
| IEA↔BSA extract | `data/legal_seed/india_bsa_iea_comparative_v1.json` |
| Lookup helpers | `app/modules/legal_compat/code_crosswalk.py` |
| Rebuild scripts | `scripts/legal_seed/build_*_from_pdf.py` |
| API | `GET/POST /api/v1/legalmitra/code-crosswalk*` |

### Source PDFs (reference backend; not edited)

| Mapping | File | Notes |
| --- | --- | --- |
| IPC ↔ BNS | `202406281710564823BNS_IPC_Comparative.pdf` | Corresponding section table |
| CrPC ↔ BNSS | `COMPARATIVE-TABLE-OF-CRPC-1973-BHARTIYA-NAGARIK-SURAKSHA-SANHITA-2023-ADV-GURENDER-RANA.pdf` | Advocate table; Sankalan overrides for high-risk |
| IEA ↔ BSA | `Bharatiya Sakshya Adhiniyam 2023 compare with Indian Evidence Act. 1872_16052024.pdf` | Comparative table; curated override for IEA 27→BSA 23 |

### Examples

| Old | New |
| --- | --- |
| IPC 420 | BNS 318(4) |
| CrPC 482 | BNSS 528 |
| IEA 65B | BSA 63 |
| IEA 25 | BSA 23(1) |

### Official reference

[NCRB Sankalan portal](https://ncrb.gov.in/uploads/SankalanPortal/Index.html) — no public API; LegalMitra keeps machine-readable extracts for lookup.

## Gap

- Some multi-line PDF rows drop a section cell (e.g. IEA 27); curated overrides fill known gaps.
- Verify contested rows against Bare Acts / Sankalan before filing.
- Does not replace RAG cite-or-refuse or human review.

## Policy reminders

- CrPC 482 → BNSS **528** (not 504/538). BNSS 504 ↔ CrPC 458.
- IPC 504 → BNS **352**. BNSS 504 is unrelated procedure.
- Always: human review required.
