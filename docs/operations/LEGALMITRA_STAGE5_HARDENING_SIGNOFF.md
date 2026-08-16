# LegalMitra Stage 5 — Agentic Workflow Hardening Sign-off

**Product:** LegalMitra  
**Date:** 2026-08-16  
**Status:** Engineering hardening **accepted** for Stage 5 Prepare Matter Response (human-gated)  
**Workspace:** `D:\sanmitra_unified-Next`

This is an **engineering** sign-off. Production enablement still requires `LEGALMITRA_AGENTIC_ENABLED=true` (defaults **off** when `ENVIRONMENT`/`APP_ENV` is production).

**Not in this sign-off:** automatic judgment retrieval for “referred cases” (next track after Stage 5).

---

## 1. Exit evidence

| Criterion | Evidence |
| --- | --- |
| E2E prepare_matter_response + audit/timeline | `tests/test_legalmitra_stage5_workflows.py` |
| RESEARCH/DRAFT human approve | Same + tracker Approve/Reject |
| RESEARCH uses Stage 2 hybrid contract | `workflow_adapters.adapter_legal_research` → `build_hybrid_legal_response` |
| Failed research cite-or-refuse | Jurisdiction miss + hybrid refusal paths |
| Retryable vs permanent | Retry UI/API; permanent cannot retry test |
| Morning Brief one-click start | Existing Stage 4 CTA |
| No file/send | Ready-to-file marker only |
| Tenant isolation | Service + HTTP tests |
| Feature flag disables routes | Prod default off; HTTP 503 when disabled |
| Tracker Retry / Cancel | `tracker.js` workflow panel |

## 2. Deferred

- Broad case-law / judgment retrieval for “referred cases”  
- KG precision eval claiming improvement over Stage 2  
- Additional catalog workflows beyond Prepare Matter Response MVP  

## 3. Commands

```powershell
D:\sanmitra_unified-Next\.venv\Scripts\python.exe -m pytest tests/test_legalmitra_stage5_workflows.py tests/test_legalmitra_stage5_http.py -q
```
