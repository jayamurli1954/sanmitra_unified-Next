# LegalMitra Stage 4 — Proactive Assistant Hardening Sign-off

**Product:** LegalMitra  
**Date:** 2026-08-16  
**Status:** Engineering hardening **accepted** for Stage 4 Morning Brief / alerts / notifications product surfaces  
**Workspace:** `D:\sanmitra_unified-Next`

This is an **engineering** sign-off. Feature flags still control production enablement; commercial adoption remains parallel.

---

## 1. Exit evidence

| Criterion | Evidence |
| --- | --- |
| Morning Brief from real tenant data; empty honest | Service + HTTP tests; tracker shows empty copy when no practice data |
| Practice Health Score | Brief API + tracker panel |
| Priority Actions by `priority_score` | Brief + alerts list |
| P0 deadline / hearing alerts | Service tests + HTTP refresh |
| Dormant / missing-doc alerts | Existing Stage 4 service tests |
| Suggested actions | Alerts + brief items |
| Tenant isolation | Service + `tests/test_legalmitra_stage4_http.py` |
| Snooze / dismiss audited | PATCH alerts UI + service/HTTP tests |
| Act-in-place deep link | `?matter_id=` + `#matter-brief` / `#document-register` consumed in tracker |
| Feature flag disable | 503 + UI disabled copy |
| Notifications inbox | Tracker panel + mark-read |

## 2. Deferred

- Weekly/monthly/quarterly brief UI  
- Full Client Health widgets  
- Email/SMS push  
- Stage 5 agentic depth beyond existing recommended-workflow CTA  

## 3. Commands

```powershell
D:\sanmitra_unified-Next\.venv\Scripts\python.exe -m pytest tests/test_legalmitra_stage4_proactive.py tests/test_legalmitra_stage4_http.py -q
```
