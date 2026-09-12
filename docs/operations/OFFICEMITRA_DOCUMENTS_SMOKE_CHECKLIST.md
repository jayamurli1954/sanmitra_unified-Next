# OfficeMitra AI — Documents package smoke checklist (ADR-016)

**Product:** OfficeMitra AI  
**Slice:** Staff Documents (CA queue list + Review note link)  
**Depends on:** ADR-015 Review notes + MitraBooks CA staff queue on `demo-mfg-mis`  
**ADRs:** [ADR-016](../adr/ADR-016-officemitra-documents-package.md) (does not supersede ADR-001 or ADR-010)

## Preconditions

1. Use **`demo-mfg-mis` only**. Do not enable `office_ai.documents` on `demo-mitrabooks-business` or production ERP tenants.
2. Tenant already has `office_ai` + `business` + a Review engagement/note (`scripts/seed_review_demo.py --run-smoke`).
3. Documents flag stays **default off** for every other tenant.

## Local seed

```text
python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
python scripts/seed_review_demo.py --run-smoke
python scripts/seed_documents_demo.py --run-smoke
```

`--run-smoke` creates one CA `bank_statement` via the MitraBooks `ca_clients` service and links an existing Review note. It does **not** post journals, upload files, or change CA document status from OfficeMitra.

`--flags-only` enables `office_ai.documents` without creating documents.

## Lifecycle under test

```text
MitraBooks CA staff queue (existing)
  → OfficeMitra Documents tab lists rows via connector
  → Link Review note → ca_document_id on OfficeMitra note
  → Unlink clears the note field; CA row remains
```

## Pass / fail

| Check | Pass |
| --- | --- |
| Ping `documents_enabled` is true only after flag | |
| Queue 403 without `office_ai.documents` | |
| Standalone without `business` returns `enabled: false` | |
| Link writes OfficeMitra note only | |
| No client portal, no CA status mutation from OfficeMitra | |
| Seed refuses `demo-mitrabooks-business` | |

## Non-goals

- Client self-portal
- OfficeMitra upload / classify / missing-doc requests
- Companion writes (ADR-010 still Proposed)
