# SanMitra Frontend Workspace

## Current State

This workspace contains browser frontends for the three target SanMitra experiences:

- `src` / `public`: MandirMitra React/MUI production frontend restored from the legacy MandirMitra layout and wired to the unified backend.
- `mitrabooks-erp`: static validation shell retained as a local/reference harness for GruhaMitra, MandirMitra, and MitraBooks workflow testing.
- `legalmitra`: separate LegalMitra experience.
- `investmitra`: separate InvestMitra experience.

The live MandirMitra frontend is no longer the lightweight static validation shell. It uses the legacy React/MUI MandirMitra user experience while calling the unified SanMitra backend with the `mandirmitra` app context. Do not copy legacy `.env` files, `node_modules`, build output, or deployment artifacts into this workspace.

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

The legacy frontends under `D:\sanmitra-backend\external-repos` still need module-by-module migration for the broader ERP target. MandirMitra is the current exception because the live domain needed the original React/MUI user experience restored before the next production-readiness pass.

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

For the restored MandirMitra React frontend:

```powershell
cd frontend
npm install
npm run build
npm start
```

If your backend is on another URL, add `?api=http://127.0.0.1:8010` to any frontend URL or set it in the on-screen API field.

## Production URL Pattern

When the `frontend/` directory is deployed as the production frontend root, the MandirMitra production URL is:

```text
https://<frontend-domain>/
```

The MandirMitra public payment page is:

```text
https://<frontend-domain>/pay
```

The MitraBooks Unified ERP static shell can also serve GruhaMitra when the host is:

```text
https://gruhamitra.sanmitratech.in/mitrabooks-erp/
https://www.gruhamitra.sanmitratech.in/mitrabooks-erp/
```

For the GruhaMitra custom domain:

- Add `gruhamitra.sanmitratech.in` and `www.gruhamitra.sanmitratech.in` to the Vercel frontend project that serves `frontend/`.
- In Hostinger DNS, create or update the GruhaMitra CNAME records to the exact targets shown by Vercel for those domains.
- Add both `https://gruhamitra.sanmitratech.in` and `https://www.gruhamitra.sanmitratech.in` to the backend Render `ALLOWED_ORIGINS` value before production smoke/E2E.

After each frontend host/domain is finalized, add the exact origin, for example `https://<frontend-domain>`, to backend `ALLOWED_ORIGINS`.

## Non-Goals

- No production UI redesign in this pass.
- No full legacy frontend merge in one step.
- No direct browser-trusted tenant override.
- No trading/order execution UI in InvestMitra.
- No LegalMitra AI assistant unless the backend enables the `legal_ai` module.
