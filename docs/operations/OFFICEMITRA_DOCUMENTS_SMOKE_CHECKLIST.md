# OfficeMitra AI — Documents package smoke checklist (ADR-016 / ADR-017)

**Product:** OfficeMitra AI  
**Slice:** Staff Documents (CA queue list + Review note link + missing-document staff tasks)  
**Depends on:** ADR-015 Review notes + MitraBooks CA staff queue on `demo-mfg-mis`  
**ADRs:** [ADR-016](../adr/ADR-016-officemitra-documents-package.md), [ADR-017](../adr/ADR-017-officemitra-missing-document-requests.md) (does not supersede ADR-001 or ADR-010)

## Preconditions

1. Use **`demo-mfg-mis` only**. Do not enable `office_ai.documents` or `office_ai.documents.requests` on `demo-mitrabooks-business` or production ERP tenants.
2. Tenant already has `office_ai` + `business` + a Review engagement/note (`scripts/seed_review_demo.py --run-smoke`).
3. Documents flags stay **default off** for every other tenant.

## Local seed

```text
python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
python scripts/seed_review_demo.py --run-smoke
python scripts/seed_documents_demo.py --run-smoke
```

`--run-smoke` creates one CA `bank_statement` via the MitraBooks `ca_clients` service, links an existing Review note, reports gaps, and raises one staff task for a missing type (`gst_returns`). It does **not** post journals, upload files, change CA document status, or email the client from OfficeMitra.

`--flags-only` enables `office_ai.documents` and `office_ai.documents.requests` without creating documents.

## Lifecycle under test

```text
MitraBooks CA staff queue (existing)
  → OfficeMitra Documents tab lists rows via connector
  → Link Review note → ca_document_id on OfficeMitra note
  → Unlink clears the note field; CA row remains
  → Gaps vs India checklist (period-matched when engagement has a period)
  → Request missing type → OfficeMitra task (optional Review note)
  → Repeat Request returns the same open task
```

## Pass / fail

| Check | Pass |
| --- | --- |
| Ping `documents_enabled` is true only after flag | **PASS** (2026-09-13) |
| Queue 403 without `office_ai.documents` | **PASS** (pytest) |
| Gaps/requests 403 without `office_ai.documents.requests` | **PASS** (pytest) |
| Standalone without `business` returns `enabled: false`; staff task still allowed | **PASS** (pytest) |
| Link writes OfficeMitra note only | **PASS** (smoke linked note `6aa60b963148f844b2eab8e0`) |
| Request creates OfficeMitra task; `client_email` is false | **PASS** (`client_email: False`, task `6aa60c76344b772a0ed17919`) |
| Repeat Request is idempotent while the task is open | **PASS** (pytest) |
| No client portal, no CA status mutation from OfficeMitra | **PASS** |
| Seed refuses `demo-mitrabooks-business` | **PASS** |

## Signoff

| Field | Value |
| --- | --- |
| Operator | Local operator smoke (`seed_documents_demo.py --run-smoke`) + pytest |
| Date | 2026-09-13 |
| Environment | local (`demo-mfg-mis`) |
| Result | **PASS** |
| Notes | Queue enabled count=1; missing_count=4; `bank_statement` present; `gst_returns` staff task created; ERP demo Review/Documents flags false; seed refuses `demo-mitrabooks-business` |

## Non-goals

- Client self-portal
- Client email / WhatsApp / SMTP
- OfficeMitra upload / classify / CA status change
- Companion writes (ADR-010 still Proposed)