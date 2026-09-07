# SanMitra Ops Alerts

**Status:** configured  
**Owner:** platform maintainer

## What you get

| Alert | Channel | When |
| --- | --- | --- |
| Daily ops digest | Same email as today | Daily 01:30 UTC (`daily-ops-check.yml`) |
| CI red | Separate `[URGENT]` email | When CI / Accounting Stability Gate / Daily Ops fails on `main` |
| LegalMitra weekly smoke | Separate email | Mondays 02:00 UTC (skips if smoke secrets missing) |

## Daily digest now includes

- Shared **backend** `/health` with postgres/mongo deep checks + live `version`
- Optional **production** backend row via `PRODUCTION_BACKEND_HEALTH_URL`
- Frontend latency warn (>500ms) and backend latency warn (>2000ms)
- SSL **WARN** when ≤21 days left → subject `SanMitra Ops [WATCH] Attention`
- Optional Vercel deploy status (needs `VERCEL_TOKEN` + `vercel_project_id` in config)
- Optional Sentry unresolved issues (existing `SENTRY_*` secrets)
- Repo `VERSION` vs live `/health.version` drift

Verdict is deterministic: `Healthy` | `Attention` | `ACTION NEEDED`. AI text stays advisory.

## Secrets / vars to set (GitHub)

Already used by daily ops:

- `SMTP_*`, `ALERT_RECIPIENT_EMAIL`, `ANTHROPIC_API_KEY` (optional AI note)
- `VERCEL_TOKEN`, `SENTRY_*`, `HEALTH_TOKEN` (optional)

New / recommended:

| Name | Purpose |
| --- | --- |
| `PRODUCTION_BACKEND_HEALTH_URL` | Override live/prod `/health` when a **separate** Render prod service exists |
| `vars.LIVE_BACKEND_HEALTH_URL` | Optional repo variable override (defaults in `ops-agents/config/services.yaml`) |
| `LEGALMITRA_SMOKE_EMAIL` | Demo LegalMitra user for weekly smoke |
| `LEGALMITRA_SMOKE_PASSWORD` | Demo password (never commit) |
| `vars.LEGALMITRA_SMOKE_API_BASE` | Optional API base override |

**Current stack (2026-08):** all prod frontends proxy to `sanmitra-unified-next-staging-sg.onrender.com`. The daily report monitors **Staging API** and **Live API (prod traffic)** on that host until a dedicated prod Render URL is deployed. Set `PRODUCTION_BACKEND_HEALTH_URL` only when prod diverges.

```powershell
# Optional — only when prod Render URL differs from staging:
gh variable set PRODUCTION_BACKEND_HEALTH_URL `
  --body "https://YOUR-PROD-SERVICE.onrender.com/health" `
  --repo jayamurli1954/sanmitra_unified-Next
```

Optional: fill `vercel_project_id` per product in `ops-agents/config/services.yaml`.

## Local dry run

```powershell
cd D:\sanmitra_unified-Next
.\.venv\Scripts\python.exe ops-agents\scripts\generate_report.py
```

Without SMTP, the report prints to stdout.

## Non-goals

- No DB credentials in CI
- No restarts / deploys / migrations from these scripts
- No production destructive E2E in the weekly smoke
