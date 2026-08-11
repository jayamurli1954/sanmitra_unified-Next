# OfficeMitra AI — Phase 4 Confirmed Write-Back Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 4 / Confirmed write-back (OfficeMitra-owned actions only)  
**Depends on:** Phase 5 standalone shell (or ERP OfficeMitra panel)  
**ADRs:** ADR-008 (Action Registry + Executor); companion products remain read-only (ADR-005)

## Preconditions

1. Tenant has `office_ai` **and** explicit `office_ai.writeback` in `enabled_modules` (or `office_ai_features`).
2. Without `office_ai.writeback`, proposal routes must 403.
3. Use demo tenant only for mutation checks.

## Lifecycle under test

```text
AI generate → pending proposal → Confirm → Action Executor → applied
                              ↘ Dismiss → dismissed (no task)
```

## API / UI smoke

### Flag gating

- [ ] `GET /api/v1/officemitra/ping` → `writeback_enabled: false` when flag absent
- [ ] `GET /api/v1/officemitra/proposals` → 403 when flag absent
- [ ] Enable `office_ai.writeback` → ping shows `writeback_enabled: true` and `registered_actions` includes `create_task`

### Proposal flow

- [ ] `POST /officemitra/tasks/generate` with `persist=true` creates **proposals**, not tasks
- [ ] Proposals tab lists pending items with Confirm / Dismiss
- [ ] Confirm → status `applied`, task created with `source=ai`, audit `proposal.apply`
- [ ] Dismiss → status `dismissed`, no new task
- [ ] Tenant B cannot confirm Tenant A proposal

### Safety

- [ ] No journal / invoice / legal / housing / temple writes from OfficeMitra
- [ ] Unknown action types fail closed (status `failed` or rejected)
- [ ] Advisory disclaimer still visible

## Exit criteria

- [ ] ADR-008 respected (action registry + human confirm + audit)
- [ ] `pytest tests/test_office_ai_phase4_writeback.py tests/test_office_ai*.py` green
- [ ] Companion write-back still deferred
