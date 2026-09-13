# OfficeMitra AI — MIS live MitraBooks smoke checklist (ADR-014 Path A)

**Product:** OfficeMitra AI  
**Slice:** Live MitraBooks MIS reads into the fact store (Phase 7a remaining)  
**Depends on:** ADR-014 Excel/export CA Analysis Pack on `demo-mfg-mis`  
**ADR:** [ADR-014](../adr/ADR-014-officemitra-ca-analysis-pack.md)  
**Plan:** [OFFICEMITRA_ADR014_LIVE_MITRABOOKS_IMPLEMENTATION_PLAN.md](../architecture/OFFICEMITRA_ADR014_LIVE_MITRABOOKS_IMPLEMENTATION_PLAN.md)

## Preconditions

1. Use **`demo-mfg-mis` only**. Do not enable `office_ai.mis.live_mitrabooks` on `demo-mitrabooks-business` or production ERP tenants.
2. Tenant already has `office_ai` + `office_ai.mis*` (import/export/pack) from `scripts/seed_mis_demo_firm.py`.
3. Live flag stays **default off** for every other tenant.
4. Expect **fail-soft** when books are empty: no invented revenue. Pytest covers Decimal mapping with monkeypatched report services; this checklist is operator confirmation on a real demo tenant.

## Local seed

```text
python scripts/seed_mis_demo_firm.py --password "ChangeMe123!"
```

Confirms nested flags include `office_ai.mis.live_mitrabooks` and a draft manufacturing pack for `2026-07` with demo (non-ledger) facts. It does **not** post journals.

Optional: if Postgres has posted MitraBooks journals for this tenant, live pull should populate `source_system=mitrabooks` facts. If not, probe/pull should warn and leave Excel/manual facts intact.

## Lifecycle under test

```text
Ping → mis_capabilities.live_mitrabooks true
  → MIS tab → Check status (GET …/mis/live-mitrabooks/status)
  → Select draft pack (period YYYY-MM)
  → Pull from MitraBooks (POST …/import/mitrabooks)
  → Facts: mitrabooks rows added/replaced; excel_import/manual kept
  → Second pull replaces mitrabooks facts only (idempotent)
  → Reconcile → second pull returns 409
  → No new PostgreSQL journal rows created by the pull
```

## Pass / fail

| Check | Pass |
| --- | --- |
| After seed, ping `mis_capabilities.live_mitrabooks` is true on `demo-mfg-mis` | |
| Live import 403 when nested flag off | |
| Probe GET returns `adr_014_live_mitrabooks` and a clear `reason` when session/business missing | |
| Pull on draft pack upserts facts with `source_system=mitrabooks` and Decimal strings (no float) | |
| Existing `excel_import` / `manual` facts remain after pull | |
| Empty books: warning / no invented revenue (Excel path still usable) | |
| Reconciled/exported pack: pull returns 409 | |
| Seed / enablement refuses `demo-mitrabooks-business` | |
| OfficeMitra did not post journals, invoices, or GST from MIS | |
| `office-ai-workspace.js` still ≤ 1253 after any UI tweak | |

## Automated coverage (already on `main`)

| Suite | Covers |
| --- | --- |
| `tests/test_office_ai_mis_live.py` | Period parse, float reject, hybrid replace, monkeypatched ingest, immutability, session required, route registration |
| `tests/test_core_route_contract_safety.py` | Live status + import/mitrabooks paths |
| `python scripts/preflight.py` | Full local CI gate before the Path A commit |

## Non-goals

- Demo `post_journal` seeder (Option B rejected by Antigravity)
- Zoho / Tally / arbitrary Excel mapper
- Client portal or client email
- Companion writes (ADR-010 still Proposed)
- Budget / prior-period live comparatives (v1 omitted)

## Signoff

| Field | Value |
| --- | --- |
| Operator | Antigravity human signoff script + checklist |
| Date | 2026-09-13 |
| Environment (local / staging) | local (`demo-mfg-mis`) |
| Result (PASS / FAIL) | **PASS** (all 9 checklist steps) |
| Notes (empty books? hybrid pack?) | Probe `empty_books` / `has_pnl_rows: false`; pull upserted 19 `mitrabooks` facts (rollup zeros OK); 38 `demo_seed` facts preserved; 0 floats; reconcile → 409; journal_entries for tenant stayed 0 (global 192 unchanged); `demo-mitrabooks-business` live flag false |

Evidence summary (2026-09-13):

- Seed + ping: `mis_capabilities.live_mitrabooks: true`
- Pack `6aa604cbb8302b66cab29a2c` period `2026-07` draft → live import → 57 facts (38 seed + 19 mitrabooks)
- Reconcile immutability and zero PostgreSQL journal mutations verified

