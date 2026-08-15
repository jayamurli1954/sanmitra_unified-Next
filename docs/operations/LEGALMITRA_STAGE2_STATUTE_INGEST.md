# LegalMitra Stage 2 statute ingest (CGST + Income-tax)

## Purpose

Load official Bare Act PDFs into LegalMitra RAG collections so hybrid research can
retrieve and cite statute sections (not only offline fallbacks).

## Source of truth for PDFs (read-only)

```text
D:\sanmitra-backend\data\legal_acts
```

Do **not** edit, move, rename, or delete files in that folder from this workspace.
Point the ingest script at it with `--pdf-dir`.

## Stage 2 acts

| Manifest key | PDF | Notes |
| --- | --- | --- |
| `cgst` | `cgst_act_2017.pdf` | ~164 sections |
| `cgst_rules` | `01062021-cgst-rules-2017-part-a-rules.pdf` | ~126 rules (refund/ITC procedure) |
| `cgst_rules_forms` | `18052021-cgst-rules-2017-part-b-forms.pdf` | Forms; statute parser yields few sections |
| `income_tax_1961` | `income_tax_act_1961.pdf` | ~458 sections (preferred IT corpus) |
| `income_tax_amended` | `income_tax_act_2025_amended.pdf` | Parser currently yields few sections; deferred |

## Commands (from `D:\sanmitra_unified-Next`)

Dry-run (no Mongo writes):

```powershell
python scripts/ingest_structured_statutes.py --pdf-dir "D:\sanmitra-backend\data\legal_acts" --only cgst cgst_rules cgst_rules_forms income_tax_1961 --dry-run
```

Ingest into Mongo (requires local Mongo configured for this workspace):

```powershell
python scripts/ingest_structured_statutes.py --pdf-dir "D:\sanmitra-backend\data\legal_acts" --only cgst cgst_rules cgst_rules_forms income_tax_1961
```

Optional embeddings (slower; needs configured embedding provider):

```powershell
python scripts/ingest_structured_statutes.py --pdf-dir "D:\sanmitra-backend\data\legal_acts" --only cgst cgst_rules income_tax_1961 --embed
```

## Current vs target

| State | Meaning |
| --- | --- |
| Current | Seed text + authorized offline slices (CGST s.54, IT s.139) work without ingest |
| After ingest | `legal_statute_sections` / `rag_chunks` hold CGST + IT 1961 section text for retrieval |
| Deferred | Full Bare Act catalog beyond Stage 2; improved 2025 IT Act parser |

## Safety

- Tenant/app for ingest defaults to `DEMO_LEGAL_TENANT_ID` (`demo-legal-firm`) /
  `legalmitra`. Override with `--tenant-id` / `--app-key` or `LEGAL_INGEST_TENANT_ID`.
  Never ingest LegalMitra RAG into `seed-tenant-1` (MandirMitra temple seed).
- No writes to `D:\sanmitra-backend`.
- No PostgreSQL / accounting changes.

## Staging enablement

Before flipping Render `LEGAL_RAG_ENABLED=true`, follow:

[`LEGALMITRA_STAGING_RAG_VERIFICATION.md`](LEGALMITRA_STAGING_RAG_VERIFICATION.md)

That runbook includes **rate-limit-safe** ingest pacing (`--sleep-ms`,
`--pause-every`) because earlier Atlas/provider ingest runs hit throttling.
