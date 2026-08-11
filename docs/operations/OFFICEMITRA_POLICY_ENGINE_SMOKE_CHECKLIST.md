# OfficeMitra AI — Policy Engine Smoke Checklist (ADR-012)

**Product:** OfficeMitra AI  
**Layer:** Policy / maker-checker governance  
**Depends on:** ADR-008 proposals + Action Capability Descriptors; ADR-009 workflows (optional)  
**ADRs:** ADR-012 Accepted

## Preconditions

1. Tenant has `office_ai` plus the feature under test (`office_ai.writeback` and/or `office_ai.workflows`).
2. Demo tenant only for mutation checks.

## Checks

### Central policy API

- [ ] `POST /api/v1/officemitra/policy/evaluate` returns structured `{allowed, execution_mode, decision, rule_id, reason, approval_expiry_hours}`
- [ ] `GET /officemitra/ping` includes `policy_engine: true`
- [ ] `GET /officemitra/actions` and `GET /officemitra/actions/create_task` expose registry + capability descriptors when writeback/workflows on

### Negative policy cases (required)

- [ ] Flag off (`office_ai.writeback` absent) → `DENY` / `POL-002`
- [ ] Same maker/checker with self-approval disabled → `DENY` / `POL-021`
- [ ] Expired approval → `DENY` / `POL-020` or proposal `expired`

### Confirmation path (LOW risk)

- [ ] Generate proposal → Confirm → applied via Action Executor
- [ ] Audit includes `policy.evaluate` and `proposal.apply` with rule ids

### Maker–checker path (HIGH / requires_maker_checker)

- [ ] Maker Confirm → status `awaiting_checker`, `approval_expires_at` set (~72h)
- [ ] Same user Approve → 403 `POL-021` (maker ≠ checker)
- [ ] Different checker Approve → applied
- [ ] After expiry → status `expired`; restart required

### Workflows

- [ ] Workflow start preflight uses policy (`required_feature=workflows`)
- [ ] Denied steps never execute companion/product writes

### Safety

- [ ] No companion mutations (ADR-010 still Proposed)
- [ ] UI and API share the same decision fields (no divergent role ifs)

## Exit criteria

- [ ] `pytest tests/test_office_ai_policy.py tests/test_office_ai_phase4_writeback.py tests/test_office_ai_phase6_workflows.py` green
- [ ] Ready to consider narrow ADR-010 allowlist behind the same policy API
