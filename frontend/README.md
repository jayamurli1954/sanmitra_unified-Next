# SanMitra Frontend Workspace

## Current State

This workspace contains clean local browser frontends for the three target SanMitra experiences:

- `mitrabooks-erp`: planned unified ERP shell for GruhaMitra, MandirMitra, and MitraBooks workflows.
- `legalmitra`: separate LegalMitra experience.
- `investmitra`: separate InvestMitra experience.

These apps are intentionally lightweight static frontends. They do not copy legacy frontend repositories, backend folders, `.env` files, `node_modules`, build output, or deployment artifacts.

Each app includes PWA fit basics:

- `viewport-fit=cover` and safe-area CSS variables.
- Touch-sized controls.
- App-height handling for mobile browser chrome.
- Per-app web manifest.
- Shared service worker for static shell caching and offline-friendly startup.

## Brand Assets

Curated image and video assets are stored in `frontend/assets/brand`.

Copied reference assets:

- `sanmitra-logo.png`
- `mitrabooks-logo.jpg`
- `mitrabooks-logo.mp4`
- `legalmitra-logo.png`
- `legalmitra-logo.mp4`
- `investmitra-logo.png`
- `mandirmitra-logo.jpeg`
- `mandirmitra-logo.mp4`
- `gruhamitra-logo.png`
- `gruhamitra-logo.mp4`

The source folders under `D:\sanmitra-backend` remain reference-only and were not modified.

## Target State

The target frontend model remains:

- MitraBooks Unified ERP for housing, temple, and accounting/business workflows.
- LegalMitra as a separate legal workflow and research frontend.
- InvestMitra as a separate investment and portfolio frontend.

## Gap

The legacy frontends under `D:\sanmitra-backend\external-repos` still need module-by-module migration. They should be used as reference only. Do not bulk-copy them into this workspace.

## Local Run

Start the unified backend separately, for example:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then serve the frontend workspace:

```powershell
python scripts\serve_frontends.py
```

Open:

- `http://127.0.0.1:3300/mitrabooks-erp/`
- `http://127.0.0.1:3300/legalmitra/`
- `http://127.0.0.1:3300/investmitra/`

If your backend is on another URL, add `?api=http://127.0.0.1:8010` to any frontend URL or set it in the on-screen API field.

## Production URL Pattern

When the `frontend/` directory is deployed as the production frontend root, the MitraBooks ERP production URL is:

```text
https://<frontend-domain>/mitrabooks-erp/
```

The MandirMitra public payment page is:

```text
https://<frontend-domain>/mandir-public/
```

After the frontend host/domain is finalized, add the exact origin, for example `https://<frontend-domain>`, to backend `ALLOWED_ORIGINS`.

## Non-Goals

- No production UI redesign in this pass.
- No full legacy frontend merge in one step.
- No direct browser-trusted tenant override.
- No trading/order execution UI in InvestMitra.
- No LegalMitra AI assistant unless the backend enables the `legal_ai` module.
