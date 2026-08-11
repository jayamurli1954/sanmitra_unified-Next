# OfficeMitra AI — Phase 5 Standalone Shell Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 5 / Standalone productivity shell (`frontend/officemitra/`)  
**Depends on:** Phase 1–2 smoke; ADR-007 modular deployment  
**ADRs:** ADR-001 … ADR-007 (read-only connectors still apply until Phase 4 / ADR-008)

## Demo tenant (standalone profile)

Provision (or reuse) a BUSINESS tenant with:

| Field | Value |
| --- | --- |
| `app_key` | `officemitra` |
| `organization_type` | `BUSINESS` |
| `enabled_modules` | `office_ai` (optionally also `office_ai.tasks`, `office_ai.email`, `office_ai.brief`, `office_ai.calendar`, `office_ai.meeting_notes`, `office_ai.notifications`) |
| Companion modules | **Not required** — no `business`, `housing`, `temple`, or `legal` |

Suggested demo id: `demo-officemitra-standalone`.

Login via unified auth (`POST /api/v1/auth/login`) with `X-App-Key: officemitra`.

## Preconditions

1. Frontend deploy includes `/officemitra/` (Vercel rewrites + host aliases for `officemitra.sanmitratech.in` / `staging.officemitra.sanmitratech.in` when DNS is ready).
2. Shared workspace module: `frontend/shared/office-ai-workspace.js` (ERP panel uses `mitrabooks`; shell uses `officemitra`).
3. AI key optional — soft-fail still allowed.

## UI / API smoke

### Auth + app key

- [ ] Open `/officemitra/login.html` (or host root → `/officemitra/`)
- [ ] Sign in with demo user; session uses shared access token storage
- [ ] `GET /api/v1/officemitra/ping` with `X-App-Key: officemitra` → `ok: true`
- [ ] ERP panel still works with `X-App-Key: mitrabooks` for OfficeMitra-entitled ERP tenants

### Phase 1–2 features in standalone shell

- [ ] Tasks: create, generate (or soft-fail), mark done
- [ ] Email paste summarize
- [ ] Calendar paste parse
- [ ] Meeting notes summarize
- [ ] Notifications list / mark read
- [ ] Today brief generate; when no companions, `deployment_mode` / connector facts indicate standalone

### Isolation / safety

- [ ] No MitraBooks ERP nav / vouchers / GST screens in the standalone shell
- [ ] No writes to Legal / Housing / Temple / journals
- [ ] InvestMitra untouched
- [ ] Tenant A cannot see Tenant B OfficeMitra data

## Exit criteria

- [ ] Standalone shell deployed and usable for `officemitra` + `office_ai`-only tenant
- [ ] ERP OfficeMitra panel still works (shared module)
- [ ] `pytest tests/test_office_ai*.py` green
- [ ] Phase 4 write-back still gated (requires ADR-008 + `office_ai.writeback`)
