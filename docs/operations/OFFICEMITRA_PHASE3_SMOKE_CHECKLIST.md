# OfficeMitra AI — Phase 3 Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 3 / Ecosystem read connectors (LegalMitra + GruhaMitra + MandirMitra)  
**Date:** 2026-08-05  
**Depends on:** Phase 1 + Phase 2 smoke signed off  
**ADRs:** ADR-001 … ADR-007 (read-only connectors; no write-back)

## Preconditions

1. Demo tenant has `office_ai` enabled.
2. To exercise each connector, also enable the companion module on that tenant:
   - Legal: `legal`
   - Housing: `housing`
   - Temple: `temple`
3. No OAuth / third-party calendar required.
4. AI key optional — deterministic brief fallback still surfaces connector sections.

## Connector expectations

| Connector | Module gate | Source (service-layer only) | Brief section key |
| --- | --- | --- | --- |
| LegalMitra | `legal` | `practice_service.list_matters` (`pending` + `draft`) | `legal_pending_documents` |
| GruhaMitra | `housing` | `housing_compat.complaints_service.list_open_complaints` | `gruhamitra_maintenance` |
| MandirMitra | `temple` | `seva_schedule_report` (upcoming posted sevas; needs Postgres session) | `mandirmitra_upcoming` |

Skipped quietly when the companion module is not enabled. Failures return empty lists — brief still generates.

**Note:** Donations are posted receipts, not due items. Phase 3 uses upcoming seva schedule as the temple “events” surface.

## UI / API smoke (MitraBooks shell → OfficeMitra AI → Today Brief)

### Legal (tenant with `legal`)

- [ ] Generate brief; `connectors_loaded` includes `legalmitra` when module enabled
- [ ] Section `legal_pending_documents` lists pending/draft matters when practice data exists
- [ ] Tenant without `legal` skips connector (`module_not_enabled`)

### Housing (tenant with `housing`)

- [ ] Open complaint exists in GruhaMitra / housing UI
- [ ] Brief section `gruhamitra_maintenance` lists that open ticket
- [ ] Resolved/closed tickets do not appear

### Temple (tenant with `temple`)

- [ ] Posted upcoming seva in window (next 14 days)
- [ ] Brief section `mandirmitra_upcoming` lists seva (no devotee mobile / PII leakage)
- [ ] Without accounting session path, connector may return empty (fail soft)

### Isolation / safety

- [ ] No writes to Legal / Housing / Temple / journals from OfficeMitra
- [ ] Connectors call product services only (no direct foreign Mongo/SQL from `office_ai`)
- [ ] InvestMitra untouched / not referenced
- [ ] Tenant A cannot see Tenant B companion facts

## Exit criteria (Phase 3)

- [ ] Three companion connectors live (not stubs) behind module gates
- [ ] Phase 1–2 features still work
- [ ] ADR-001…007 respected; Phase 4 write-back still deferred
- [ ] `pytest tests/test_office_ai*.py` green locally
