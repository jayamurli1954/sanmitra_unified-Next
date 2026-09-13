# OfficeMitra — ADR-014 remaining slice: live MitraBooks MIS reads

**Status:** Antigravity **APPROVE** (2026-09-12) — Path A live MitraBooks MIS ingest **implemented** behind `office_ai.mis.live_mitrabooks` (default off). Operator smoke **PASS** 2026-09-13 on `demo-mfg-mis` ([checklist](../operations/OFFICEMITRA_MIS_LIVE_SMOKE_CHECKLIST.md)).
**ADR:** [ADR-014](../adr/ADR-014-officemitra-ca-analysis-pack.md) (Accepted 2026-08-11)
**Date:** 2026-09-12
**Audience:** Core engineering / operators

Excel import, packs, narrative, reconcile, Excel/PDF/PPT export, and live Path A report-service ingest ship on this branch behind `office_ai.mis*`. Zoho/Tally and ADR-010 companion writes remain out of scope.

---

## 0. Reviewer brief (Antigravity)

Please return one of:

| Verdict | Meaning |
| --- | --- |
| **Approve** | Implement this remaining slice as written. |
| **Approve with changes** | List required edits; do not start code until those edits are in this file. |
| **Reject** | Name the blocking issue. Do not implement live MIS ingest. |

Review against: [ADR-014](../adr/ADR-014-officemitra-ca-analysis-pack.md), [ADR-002](../adr/ADR-002-officemitra-connector-manager.md), [ADR-010](../adr/ADR-010-officemitra-companion-writeback.md) (still **Proposed**), AGENTS.md §13a, accounting doctrine (Decimal / no float / no ledger writes from OfficeMitra), and the locked decisions below.

**Do not expand this slice into:** Zoho/Tally ingest, arbitrary Excel mapping, client portal, client email, journal/invoice/GST writes, or ADR-010 companion write-back.

---

## 1. Locked product decisions (do not reopen)

These are already locked for OfficeMitra. This slice inherits them.

| ID | Decision |
| --- | --- |
| D1 | OfficeMitra is a package inside the existing brand. No new Mitra product names. |
| D2 | Review, Documents, and MIS are OfficeMitra workspaces/packages, not new brands. |
| D3 | InvestMitra stays out of unified scope. |
| D4 | Knowledge and legal notices stay LegalMitra unless a later ADR composes them. |
| D5 | Enablement for this slice: **`demo-mfg-mis` only**. Refuse `demo-mitrabooks-business` and production ERP tenants. |
| D6 | MIS **never** posts journals, creates invoices, or files GST. Companion **writes** stay blocked until ADR-010 is Accepted. **Reads** of MitraBooks reports are in-scope for this slice (ADR-014 / ADR-002). |
| D7 | Live ingest calls **accounting report services only**. No raw SQL against PostgreSQL from OfficeMitra code. No Mongo queries of MitraBooks collections from OfficeMitra code except via the existing connector. |
| D8 | Facts remain immutable after reconcile/export. Live pull is allowed only while the pack is `draft` or `pending_reconcile`. |
| D9 | Money is `Decimal` / integer minor units. Never `float` in new ingest mapping. |
| D10 | Parent flag `office_ai.mis` remains required. Nested flag **`office_ai.mis.live_mitrabooks`** already exists (default off) and gates this slice. |
| D11 | `frontend/shared/office-ai-workspace.js` stays at or below the grandfather **1253** (current **1252**). Live-pull UI must not grow that file. |
| D12 | `app/modules/office_ai/router.py` must not grow past its file-size grandfather. New live-ingest routes go in a **new** router file (same pattern as `documents_router.py` / `mis_narrative_router.py`). |

---

## 2. Honest current vs target vs gap

### Current (already on `origin/main`)

| Piece | Status |
| --- | --- |
| Registry helpers `is_office_ai_mis_enabled`, `.import`, `.export`, `.live_mitrabooks`, `.pack.<key>` | Done |
| Mongo fact/pack store, Excel template import, narrative + citations | Done |
| Reconcile immutability; Excel / PDF / PPT export; PPT blocked when `data_quality_score` &lt; 70 | Done |
| Routes under `/api/v1/officemitra/mis/*` (status, catalog, packs, facts, import/excel, reconcile, export, narrative) | Done |
| UI MIS tab: `office-ai-workspace.js` + `office-ai-mis-dashboard.js` | Done |
| Tests: `tests/test_office_ai_mis.py` | Done |
| Demo seed: `scripts/seed_mis_demo_firm.py` for `demo-mfg-mis` | Done — enables import/export/`pack.manufacturing`; **does not** enable `office_ai.mis.live_mitrabooks` |
| Ping already reports `mis_capabilities.live_mitrabooks` | Done — flag exists; **no ingest route** |

Brief connectors `get_todays_revenue` / `get_overdue_invoices` in `mitrabooks_connector.py` remain **Daily Brief** reads. They are **not** the MIS fact store and must not be aliased to pack facts.

### Target (this slice only)

Staff on `demo-mfg-mis` with `office_ai.mis` **and** `office_ai.mis.live_mitrabooks` can:

1. Open an existing draft MIS pack (or create one).
2. Pull live MitraBooks P&amp;L, balance sheet, cash receipts/payments, and AR/AP ageing **for the pack period**.
3. Persist those numbers as MIS facts with `source_system=mitrabooks` and `ingestion_path=mitrabooks`.
4. Use the **existing** narrative / reconcile / export flow unchanged.
5. See fail-soft copy when `business`/`accounting` is off, Postgres session is missing, or books are empty — **no invented numbers**.

### Gap

| Missing | Notes |
| --- | --- |
| Connector mapping from report services → `MISFact` | Not built |
| `POST …/mis/packs/{pack_id}/import/mitrabooks` (or equivalent) | Not built |
| Seed flag `office_ai.mis.live_mitrabooks` on `demo-mfg-mis` | Intentionally off today |
| Operator smoke that a live pull fills facts from posted demo books | Not run |
| UI control “Pull from MitraBooks” | Not built; must live outside `office-ai-workspace.js` |

---

## 3. Non-goals (explicit)

Do **not** include in this PR:

- ADR-010 companion writes (upload CA files, change CA status, post journals from OfficeMitra).
- Zoho Books, Tally, or arbitrary Excel column mapping (ADR-014 deferred Path B/C/D).
- Client portal, client email, or “request from client” on MIS packs.
- Rebuilding Excel import, PPT templates, or narrative (already shipped).
- Growing `office-ai-workspace.js` or `office_ai/router.py`.
- Enabling live MIS on `demo-mitrabooks-business` or any production tenant.
- Using Daily Brief `get_overdue_invoices` (currently uses `float`) as the MIS ageing source. Ageing for MIS must go through `allocation_service.ar_ap_aging` (or equivalent Decimal report) and map with `Decimal`.
- Treating empty books as success with placeholder KPIs.

---

## 4. Flag and access

| Flag | Default | Requires |
| --- | --- | --- |
| `office_ai.mis` | off | module `office_ai` |
| `office_ai.mis.live_mitrabooks` | off | parent `office_ai.mis` |

Access decision (same pattern as Documents / Review):

1. Authenticated user; trusted `tenant_id` (never from body).
2. Module `office_ai` enabled.
3. `office_ai.mis` enabled.
4. `office_ai.mis.live_mitrabooks` enabled — else **404** on the live-import route (same nested-dot style as `office_ai.review.notes` / `office_ai.documents.requests`).
5. Fail-soft when companion `business` or accounting session is unavailable: HTTP 200 with `enabled: false` and a reason string on a **status/probe** helper; the POST import returns **400/503** with a clear message, never fake facts.

Ping: keep `mis_capabilities.live_mitrabooks`. Add `adr_014_live_mitrabooks: true` on the new route envelope if useful for UI gating (optional).

---

## 5. Proposed API

New router file (do not grow `office_ai/router.py`):

`app/modules/office_ai/mis_live_router.py`

Mounted with existing OfficeMitra routers.

### `POST /api/v1/officemitra/mis/packs/{pack_id}/import/mitrabooks`

**Gates:** `require_enabled_module_feature("office_ai", "mis.live_mitrabooks")` (or equivalent nested helper already used for `review.notes`).

**Body (all optional except as noted):**

```json
{
  "accounting_entity_id": "primary"
}
```

- `pack_id` from path; pack must belong to trusted `tenant_id`.
- Period comes from the pack (`period` like `2026-07`), not from an untrusted body date range.
- `accounting_entity_id` defaults to `primary` if omitted.

**Behavior:**

1. Load pack; 404 if missing / wrong tenant.
2. 409 if pack status is reconciled or exported (`MISImmutableError`).
3. Resolve `from_date` / `to_date` / `as_of` from pack period (see §7).
4. Call connector read helpers (report services only) with trusted `tenant_id`, trusted `app_key`, and `accounting_entity_id`.
5. Map results to `MISFact` rows (`source_system=mitrabooks`, `ingestion_path=mitrabooks`).
6. **Replace only** existing facts on this pack with `source_system=mitrabooks`. Leave `excel_import` / `manual` facts in place (hybrid pack allowed).
7. Set pack `ingestion_path` to `mitrabooks` if it was `manual`/empty; if the pack already has Excel facts, leave `ingestion_path` as-is or set a documented hybrid note in the response — **review question Q3**.
8. Recompute `data_quality_score` using the existing scorer.
9. Return `{ pack, facts_upserted, facts_replaced, warnings[] }`.

**Idempotency:** a second POST on the same draft pack replaces the previous mitrabooks-sourced facts for that pack. It is not a journal posting, so `X-Idempotency-Key` is not required. No PostgreSQL writes.

### Probe (optional, recommended)

`GET /api/v1/officemitra/mis/live-mitrabooks/status`

Returns whether the flag is on, whether a DB session is available, and whether the connector can see any P&amp;L/BS rows for the current month — **no fact writes**. Useful for the UI empty state.

---

## 6. Connector (ADR-002)

Extend `app/modules/office_ai/connectors/mitrabooks_connector.py` with **new** MIS-named helpers. Do **not** overload Daily Brief `collect()` for pack ingest.

Proposed helpers (names can change if review prefers):

| Helper | Calls (services only) | Maps to entity types (illustrative) |
| --- | --- | --- |
| `get_mis_profit_loss(...)` | `app.accounting.reports.get_profit_loss` | `revenue`, `expense`, `net_profit` |
| `get_mis_balance_sheet(...)` | `app.accounting.reports.get_balance_sheet` | `asset`, `liability`, `equity` (totals + material lines if needed) |
| `get_mis_cash_movement(...)` | `app.accounting.reports.get_receipts_payments` | `cash_in`, `cash_out`, `net_cash` |
| `get_mis_ar_ap_aging(...)` | `app.modules.business.allocation_service.ar_ap_aging` | `ar_outstanding`, `ap_outstanding` (and bucket totals if the pack catalog expects them) |

Rules:

- Pass `session: AsyncSession` from FastAPI accounting session dependency (same fail-soft as `get_todays_revenue` when session is missing).
- Pass trusted `tenant_id` and trusted `app_key` from request context. **Do not** hardcode `mandirmitra` (report-service default). **Do not** silently use `CA_QUEUE_APP_KEY` unless review chooses that (Q2).
- Convert every amount with `Decimal`; persist `amount_decimal` string and `amount_minor` per existing `MISFact` schema.
- Empty books → `warnings[]` + zero or omitted optional facts; **never** invent revenue.
- Standalone OfficeMitra without `business`: helpers return `enabled: false`; POST import fails with a clear 400.

A thin `mis_live_ingest.py` (or functions on `mis_service`) owns mapping + replace semantics so the connector stays a read adapter.

---

## 7. Period and entity mapping

Packs today store `period` as a string (demo uses `2026-07`).

**Proposed v1 rule:**

- If `period` matches `YYYY-MM`, then:
  - `from_date` = first day of that month
  - `to_date` = last day of that month
  - `as_of` = `to_date` (balance sheet and ageing)
- If `period` is a full date or `YYYY-MM-DD..YYYY-MM-DD`, parse explicitly.
- Otherwise 400: `unsupported_period`.

Budget / prior-period comparatives are **out of this slice** unless review mandates them (Q6). Missing budget facts should continue to lower `data_quality_score` via the existing scorer rather than blocking the pull.

`accounting_entity_id` defaults to `primary`.

---

## 8. UI

- **Do not** add live-pull controls to `office-ai-workspace.js`.
- Add a “Pull from MitraBooks” button and result/warning copy on `frontend/shared/office-ai-mis-dashboard.js` (or a new `office-ai-mis-live.js` imported by the dashboard — Q7).
- Show the control only when ping/status says `live_mitrabooks` is enabled.
- After pull, reuse existing pack/facts/narrative widgets.
- Copy when books are empty: facts were not invented; import Excel or post demo vouchers first.

---

## 9. Demo seed and smoke

**Seed change (demo-mfg-mis only):**

- Set nested flag `office_ai.mis.live_mitrabooks: true` in `scripts/seed_mis_demo_firm.py` (still refuse other tenant ids).
- Do **not** enable the flag in `seed_review_demo.py` / Documents seeds unless those tenants are `demo-mfg-mis`.

**Posted books for smoke (Q4 — needs review):**

Option A (recommended to ask): live-pull smoke is **fail-soft** if the demo tenant has no journals; pytest uses **monkeypatched report services** returning Decimal fixtures. Operator smoke on staging is a separate checklist after real demo vouchers exist.

Option B: a **demo-only** seeder calls the **accounting service** `post_journal` (not OfficeMitra) to post a tiny balanced pair on `demo-mfg-mis`. That is MitraBooks demo data, not MIS writing the ledger. Requires explicit reviewer OK because it is `[CRITICAL-ACCOUNTING]` even on demo.

This plan defaults to **Option A** unless Antigravity selects B.

**Operator smoke (after code, `demo-mfg-mis` only):** use [`OFFICEMITRA_MIS_LIVE_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_MIS_LIVE_SMOKE_CHECKLIST.md).

1. Seed MIS demo; confirm ping `live_mitrabooks: true`.
2. Create or open a draft pack for `2026-07`.
3. POST import/mitrabooks.
4. Confirm facts with `source_system=mitrabooks` and no float in stored amounts.
5. Confirm Excel-imported facts (if any) were not deleted.
6. Reconcile still locks; second pull returns 409.
7. Confirm `demo-mitrabooks-business` seed/scripts still refuse this flag.
8. Confirm no new PostgreSQL journal rows were created by the import.

---

## 10. Tests

Extend `tests/test_office_ai_mis.py` (or add `tests/test_office_ai_mis_live.py` if the file would exceed a sensible size):

| Test | Expect |
| --- | --- |
| Flag off | live import 404 |
| Flag on, pack missing | 404 |
| Flag on, wrong tenant pack id | 404 |
| Reconciled pack | 409 |
| Monkeypatched P&amp;L/BS/cash/ageing | facts persisted with `source_system=mitrabooks`, Decimal strings |
| Second pull | mitrabooks facts replaced; excel facts kept |
| No DB session / business disabled | 400/503, zero facts written |
| Empty report payload | 200 or 400 with warnings; no invented revenue |
| Body `tenant_id` ignored | trusted context only |
| Route contract | new paths in `scripts/frontend_backend_route_contract.py` allowlist |
| Money | no `float` in mapping unit tests |

Do **not** hit production-like tenants. Do **not** assert on live Render data in pytest.

---

## 11. Docs to update **after** code (not in this plan PR)

When implementation is approved and merged:

- AGENTS.md §13a — live MitraBooks MIS reads behind `office_ai.mis.live_mitrabooks`; still no journal writes.
- `docs/architecture/CURRENT_VS_TARGET.md` — remaining MIS row: live reads **done**; Zoho/Tally still deferred.
- `docs/architecture/MODULE_REGISTRY.md` — document that the existing flag now has a route.
- `docs/architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md` Phase 7a remaining work.
- ADR-014 sequencing step 8 marked Done **only after** tests + demo smoke.

This plan file stays the spec until then.

---

## 12. File-size and module boundaries

| File | Rule |
| --- | --- |
| `frontend/shared/office-ai-workspace.js` | ≤ 1253; no live-pull UI here |
| `app/modules/office_ai/router.py` | do not grow; new `mis_live_router.py` |
| `mitrabooks_connector.py` | add read helpers; do not query CA Mongo or journal tables |
| `mis_store.py` | reuse `replace`/`delete` for `source_system=mitrabooks` only; do not weaken immutability |

After code: `graphify update .`, then `python scripts/preflight.py`.

---

## 13. Security and tenancy

- Trusted `tenant_id` / `app_key` / `user_id` from auth dependencies only.
- Every Mongo fact/pack query remains tenant-scoped (existing store).
- Report-service calls remain tenant-scoped.
- No secrets in logs. Do not log full report payloads in production logs.
- No PII export beyond existing MIS export artifacts.

---

## 14. Rollback

- Flag default remains **off**. Turning the nested flag off hides the route (404).
- Facts already pulled on a draft pack remain until operator discards/revises the pack; they are Mongo MIS facts, not ledger rows.
- No PostgreSQL migration in this slice.
- Rollback of a bad mapping is: disable flag + leave Excel path as the supported ingest.

---

## 15. Review questions — Antigravity answers (locked 2026-09-12)

| Q | Decision |
| --- | --- |
| **Q1** | Live Path A ingest + tests + demo flag only. Do not rebuild Excel/narrative/export. |
| **Q2** | Default report-service `app_key = "mitrabooks"` (same convention as `CA_QUEUE_APP_KEY`). Request `officemitra` must not be passed to `_gl_sums_by_account`. |
| **Q3** | Hybrid packs: replace only `source_system=mitrabooks` facts; keep `excel_import` / `manual`. |
| **Q4** | Option A: pytest monkeypatch + fail-soft empty books. No demo `post_journal` seeder in this slice. |
| **Q5** | `YYYY-MM` → calendar month; explicit range `YYYY-MM-DD..YYYY-MM-DD` allowed; else `400 unsupported_period`. |
| **Q6** | Omit live budget/prior-period comparatives in v1; missing budget may lower `data_quality_score`. |
| **Q7** | New module `frontend/shared/office-ai-mis-live.js` imported by `office-ai-mis-dashboard.js`. |
| **Q8** | Include `GET /api/v1/officemitra/mis/live-mitrabooks/status` in v1. |
| **Q9** | Pull both AR and AP in one import. |
| **Q10** | `demo-mfg-mis` only; never `demo-mitrabooks-business`. |

---

## 16. Suggested implementation order (after Approve)

1. Connector helpers + Decimal mapping unit tests (monkeypatch report services).
2. `mis_live_router.py` + store replace-by-`source_system` + route contract.
3. Dashboard (or new JS) button; ping already has the capability bit.
4. Seed nested flag on `demo-mfg-mis` only.
5. Docs listed in §11.
6. `graphify update .` + `python scripts/preflight.py`.

Do not start this list until Antigravity returns **Approve** or **Approve with changes** and those changes are written back into this file.

---

## 17. Acceptance criteria for the future code PR

- [ ] Live import gated on `office_ai.mis.live_mitrabooks` (parent `office_ai.mis` required).
- [ ] Report services only; no raw SQL; no journal/invoice/GST writes.
- [ ] Facts use Decimal strings / minor units; tests fail if mapping uses `float`.
- [ ] Reconciled/exported packs cannot be pulled into (409).
- [ ] Tenant isolation tests pass.
- [ ] `office-ai-workspace.js` still ≤ 1253; `office_ai/router.py` not grown.
- [ ] Seed refuses any tenant other than `demo-mfg-mis`.
- [ ] AGENTS / CURRENT_VS_TARGET / MODULE_REGISTRY / Phase 7a updated.
- [ ] `python scripts/preflight.py` passed before push.
- [ ] Current vs target language: live reads implemented; Zoho/Tally/ADR-010 still not.

---

## 18. Plan status

**Plan only.** Excel/export CA Analysis Pack is already implemented. Live MitraBooks MIS ingest is **not** implemented until a later PR that follows this document after Antigravity review.
