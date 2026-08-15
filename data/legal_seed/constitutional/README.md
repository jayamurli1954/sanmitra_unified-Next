# LegalMitra Tier-1 Constitutional Seed Data

**Generated for**: LegalMitra (SanMitra Unified Platform)  
**Version**: 1.0  
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
| File | Doctrine | Priority |
|------|----------|----------|
| `basic_structure.json` | Basic Structure Doctrine | Critical |
| `stare_decisis.json` | Doctrine of Stare Decisis / Precedent (Art. 141) | Critical |
| `ultra_vires.json` | Doctrine of Ultra Vires | Critical |
| `severability.json` | Doctrine of Severability | Critical |
| `eclipse.json` | Doctrine of Eclipse | Critical |
| `doctrine_index.json` | Master index of all doctrines | — |

### Landmark Judgments (`constitutional/landmark_judgments/`)
| File | Case | Citation | Year |
|------|------|----------|------|
| `kesavananda_bharati_1973.json` | Kesavananda Bharati v. State of Kerala | (1973) 4 SCC 225 | 1973 |
| `minerva_mills_1980.json` | Minerva Mills Ltd. v. Union of India | (1980) 3 SCC 625 | 1980 |
| `maneka_gandhi_1978.json` | Maneka Gandhi v. Union of India | (1978) 1 SCC 248 | 1978 |
| `sr_bommai_1994.json` | S.R. Bommai v. Union of India | (1994) 3 SCC 1 | 1994 |
| `landmark_index.json` | Master index of all judgments | — | — |

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

## Next Recommended Additions (Tier-2)

- Proportionality doctrine + Modern Dental College / Om Kumar
- I.R. Coelho (2007)
- K.S. Puttaswamy (2017) – Privacy
- Golaknath (1967)
- Colourable Legislation, Pith & Substance, Occupied Field
- More High Court landmark decisions of pan-India importance

---

*These files are intended as high-quality, source-grounded seed data. Always verify critical legal propositions against the original judgments before production use.*
