# LegalMitra Stage 6 — Practice Billing Hardening Sign-off

**Product:** LegalMitra  
**Date:** 2026-08-16  
**Status:** Engineering hardening **accepted** for Stage 6 native fee ledger  
**Workspace:** `D:\sanmitra_unified-Next`

This is an **engineering** sign-off. Production billing still requires
`LEGALMITRA_BILLING_ENABLED=true` (defaults **off** when `ENVIRONMENT`/`APP_ENV`
is production). MitraBooks GL posting remains opt-in via
`LEGALMITRA_MITRABOOKS_POSTING_ENABLED` + explicit confirm.

---

## 1. Exit evidence

| Criterion | Evidence |
| --- | --- |
| Create → issue → collect + audit | `tests/test_legalmitra_stage6_billing.py`, HTTP suite |
| Tracker live fee summary | `tracker-fee-ledger.js` + dashboard fees_outstanding |
| Partial payment + void | Service + HTTP tests |
| Feature flag disables routes | Prod default off; HTTP 503 when disabled |
| Tenant isolation | Service + HTTP tests |
| No silent MitraBooks post | confirm + flag required (existing tests) |
| Tracker Issue / Collect / Void | `tracker-fee-ledger.js` actions |
| Collect without Postgres | `get_optional_async_session` — Mongo collect does not require PG |

## 2. Deferred

- Broad MitraBooks posting enablement for paying tenants  
- Full invoice UX / GST e-invoice IRN  
- Multi-product AI brain  

## 3. Commands

```powershell
D:\sanmitra_unified-Next\.venv\Scripts\python.exe -m pytest tests/test_legalmitra_stage6_billing.py tests/test_legalmitra_stage6_http.py -q
```
