# LegalMitra Constitutional Seed Data

**Generated for**: LegalMitra (SanMitra Unified Platform)  
**Version**: 1.1  
**Date**: 2026-08-15  
**Purpose**: High-quality seed corpus for constitutional doctrines and landmark judgments to power RAG-based legal research.

## Current vs target

- **Current:** These JSON files live in the repo under `data/legal_seed/constitutional/` and `data/legal_seed/crosswalks/`. They are curated **summaries with citations**, not full judgment text, and they are **not** auto-ingested into `rag_documents`.
- **Target:** Operator ingest into a tenant-scoped LegalMitra RAG collection so research answers can cite these doctrines and landmark holdings.
- **Gap:** Run `python scripts/ingest_legal_constitutional_seed.py --dry-run` then ingest for a demo/seed tenant. Production enablement still requires the original reported decisions, quality-gate checks, and human review.

Dry-run (no Mongo writes):

```powershell
python scripts/ingest_legal_constitutional_seed.py --dry-run
```

## Contents

### Doctrines (`constitutional/doctrines/`)
| File | Doctrine | Priority | Tier |
|------|----------|----------|------|
| `basic_structure.json` | Basic Structure Doctrine | Critical | 1 |
| `stare_decisis.json` | Doctrine of Stare Decisis / Precedent (Art. 141) | Critical | 1 |
| `ultra_vires.json` | Doctrine of Ultra Vires | Critical | 1 |
| `severability.json` | Doctrine of Severability | Critical | 1 |
| `eclipse.json` | Doctrine of Eclipse | Critical | 1 |
| `doctrine_index.json` | Master index of all doctrines | — | — |

### Landmark Judgments (`constitutional/landmark_judgments/`)
| File | Case | Citation | Year | Tier |
|------|------|----------|------|------|
| `kesavananda_bharati_1973.json` | Kesavananda Bharati v. State of Kerala | (1973) 4 SCC 225 | 1973 | 1 |
| `minerva_mills_1980.json` | Minerva Mills Ltd. v. Union of India | (1980) 3 SCC 625 | 1980 | 1 |
| `maneka_gandhi_1978.json` | Maneka Gandhi v. Union of India | (1978) 1 SCC 248 | 1978 | 1 |
| `sr_bommai_1994.json` | S.R. Bommai v. Union of India | (1994) 3 SCC 1 | 1994 | 1 |
| `golaknath_1967.json` | I.C. Golaknath v. State of Punjab | AIR 1967 SC 1643 | 1967 | 2 |
| `indira_nehru_gandhi_1975.json` | Indira Nehru Gandhi v. Raj Narain | (1975) Supp SCC 1 | 1975 | 2 |
| `puttaswamy_2017.json` | K.S. Puttaswamy v. Union of India | (2017) 10 SCC 1 | 2017 | 2 |
| `navtej_singh_johar_2018.json` | Navtej Singh Johar v. Union of India | (2018) 10 SCC 1 | 2018 | 2 |
| `shreya_singhal_2015.json` | Shreya Singhal v. Union of India | (2015) 5 SCC 1 | 2015 | 2 |
| `vishaka_1997.json` | Vishaka v. State of Rajasthan | (1997) 6 SCC 241 | 1997 | 2 |
| `indra_sawhney_1992.json` | Indra Sawhney v. Union of India | 1992 Supp (3) SCC 217 | 1992 | 2 |
| `hussainara_khatoon_1979.json` | Hussainara Khatoon v. State of Bihar | (1980) 1 SCC 81 | 1979 | 2 |
| `olga_tellis_1985.json` | Olga Tellis v. Bombay Municipal Corporation | (1985) 3 SCC 545 | 1985 | 2 |
| `landmark_index.json` | Master index of all judgments | — | — | — |

### Crosswalks (`crosswalks/`)
- `doctrine_to_cases.json` — Mapping between doctrines and supporting judgments

## Schema Notes

Each doctrine and judgment file follows a consistent structure designed for easy ingestion into the existing LegalMitra RAG pipeline:

- `content_for_rag` — Clean, well-written prose suitable for chunking and embedding
- `legal_metadata`-compatible fields (`jurisdiction`, `court_name`, `citation`, `practice_area`, `matter_type`, `doc_date`, etc.)
- Rich `tags` for improved retrieval
- Explicit links to related articles, supporting cases, and doctrines

## Ingestion Guidance

When ingesting into `rag_documents` / `rag_chunks`:

1. Use `source_type`: `"doctrine"` or `"judgment"`
2. Map fields into `RagLegalMetadata`
3. Prefer section-level or paragraph-level chunking of `content_for_rag`
4. Preserve `tags` and citation metadata for filtering and citation generation

## Next recommended additions (deferred)

- Proportionality doctrine (Om Kumar / Modern Dental College) as a structured doctrine file
- I.R. Coelho (2007)
- Colourable legislation, pith and substance, occupied field
- More High Court landmark decisions of pan-India importance

---

*These files are intended as high-quality, source-grounded seed data. Always verify critical legal propositions against the original judgments before production use.*
