# OfficeMitra AI — Phase 6 Workflow Engine Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 6 / Workflow engine (OfficeMitra-owned actions only)  
**Depends on:** Phase 4 write-back (ADR-008 Action Registry + Executor)  
**ADRs:** ADR-009 Accepted; companion products remain read-only (ADR-005 / ADR-010 Proposed)

## Preconditions

1. Tenant has `office_ai` **and** explicit `office_ai.workflows` in `enabled_modules` (or `office_ai_features`).
2. Without `office_ai.workflows`, workflow routes must 403.
3. Use demo tenant only for mutation checks.

## Lifecycle under test

```text
Workflow Template (reusable, versioned)
        ↓ start + idempotency_key + trigger_source
Workflow Run
        ↓ steps via Action Executor (office_ai only)
Step results (duration_ms, retry_count, executor_version, error_message)
```

Default: **stop-on-failure** (remaining steps → `skipped`).

## API / UI smoke

### Flag gating

- [ ] `GET /api/v1/officemitra/ping` → `workflows_enabled: false` when flag absent
- [ ] `GET /api/v1/officemitra/workflows/templates` → 403 when flag absent
- [ ] Enable `office_ai.workflows` → ping shows `workflows_enabled: true` and actions include `create_task` / `create_notification`

### Template vs run

- [ ] `POST /officemitra/workflows/templates` creates template with `version`, `created_by`, ordered steps
- [ ] Workflows tab lists templates separately from runs
- [ ] `POST /officemitra/workflows/runs` with `trigger_source=manual` executes steps
- [ ] Run stores `template_id`, `template_version`, `trigger_source`, step diagnostics

### Idempotency

- [ ] Same `idempotency_key` returns existing run (`idempotent_replay: true`) without duplicate tasks
- [ ] Double-click Start does not create two applied runs for the same key

### Failure policy

- [ ] Force a step failure → run `failed`, later steps `skipped` when `continue_on_failure=false`
- [ ] No silent partial success

### Safety

- [ ] No journal / invoice / legal / housing / temple writes from workflow steps
- [ ] Unknown `action_type` rejected at template create
- [ ] Tenant B cannot list/start Tenant A templates
- [ ] Advisory disclaimer still visible

## Exit criteria

- [ ] ADR-009 respected (template ≠ run, executor reuse, diagnostics, idempotency, stop-on-failure)
- [ ] `pytest tests/test_office_ai_phase6_workflows.py tests/test_office_ai_phase4_writeback.py` green
- [ ] Companion write-back still deferred (ADR-010)
