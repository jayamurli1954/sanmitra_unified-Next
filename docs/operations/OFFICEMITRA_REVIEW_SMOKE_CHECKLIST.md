# OfficeMitra AI — Review workspaces smoke checklist (ADR-015)

**Product:** OfficeMitra AI  
**Slice:** Review / working papers / review notes  
**Depends on:** ADR-014 MIS pack on `demo-mfg-mis`  
**ADRs:** [ADR-015](../adr/ADR-015-officemitra-review-workspaces.md) (does not supersede ADR-001)

## Preconditions

1. Use **`demo-mfg-mis` only**. Do not enable `office_ai.review*` on `demo-mitrabooks-business` or production ERP tenants.
2. Tenant already has `office_ai` + `office_ai.mis*` and a MIS pack (run `scripts/seed_mis_demo_firm.py` first).
3. Review flags stay **default off** for every other tenant.

## Local seed

```text
python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
python scripts/seed_review_demo.py --run-smoke
```

`--run-smoke` links the MIS pack, scans facts, generates five Excel papers, creates a note, and closes it. It does **not** post MitraBooks journals.

`--flags-only` enables `office_ai.review*` without creating engagements.

## Lifecycle under test

```text
MIS pack (Excel facts) → engagement → scan findings + risk score
                       → working papers (Cash/AR/AP lead + ageing)
                       → review note → OfficeMitra task → close note
```

## API / UI smoke

### Flag gating

- [x] `GET /api/v1/officemitra/ping` on an ERP tenant without Review → `review_enabled: false` and no Review tab
- [x] Review routes → 403 when `office_ai.review` is absent *(covered by `tests/test_office_ai_review.py`)*
- [x] Working-papers / notes routes → 403 when nested flags are absent *(covered by pytest)*
- [x] `demo-mfg-mis` after seed → ping `review_enabled: true`, `review_capabilities.working_papers` and `.notes` true

### Review flow (`demo-mfg-mis`)

- [x] Login as `admin@demo-mfg-mis.local` → OfficeMitra AI → **Review** tab visible *(in-process smoke + entitlements; UI login optional follow-up)*
- [x] Create or select engagement for period `2026-07` with the seeded MIS pack id
- [x] Scan shows coded findings (expect `AR_AGING_90` / `AP_AGING_90` from 90+ buckets; `61-90` is not 90+)
- [x] Risk score is `engagement_risk_score`, not MIS `data_quality_score`
- [x] Generate working papers → five Excel files; download one; close one (immutable)
- [x] Create a note → OfficeMitra task created; Close note → status `closed`
- [x] Copy states Review does not post to the live MitraBooks ledger

### Safety

- [x] No journal / invoice / GST / housing / temple writes from Review
- [x] Tenant B cannot list Tenant A engagements *(pytest)*
- [x] SSDV CLI is not invoked (`ssdv_cli: false`)
- [x] Live MitraBooks ERP screens (parties, vouchers, GST, bank rec) unchanged

## Exit criteria

- [x] `pytest tests/test_office_ai_review.py tests/test_office_ai_mis.py -q` green
- [x] Local `--run-smoke` printed `ledger: no MitraBooks journals posted`
- [x] Flags remain off on `demo-mitrabooks-business` and production
- [x] Deferred packages (client portal, compliance, knowledge, notices, advisory) not started

## Signoff

| Field | Value |
| --- | --- |
| Operator | Local operator smoke (`seed_review_demo.py --run-smoke`) + pytest |
| Date | 2026-09-13 |
| Environment | local (`demo-mfg-mis`) |
| Result | **PASS** |
| Notes | Engagement `6aa60b963148f844b2eab8d7`; pack `6aa604cbb8302b66cab29a2c`; issues=2 risk=35 `data_quality_score=None` `ssdv_cli=False`; papers=5; note closed; codes `AR_AGING_90`, `AP_AGING_90`; ERP demo flags all false |