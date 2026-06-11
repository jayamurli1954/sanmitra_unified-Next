# Deployment Status Check - MitraBooks

## Current State

- Repository: `sanmitra_unified-Next`
- Branch: `main`
- Latest pushed MitraBooks work: landing pages, settings menu, onboarding/pricing plan, and MitraBooks pricing catalog.
- Local validation for the latest MitraBooks work passed before push:
  - `python -m pytest tests/test_gruhamitra_pricing.py tests/test_mitrabooks_frontend_local_api.py -q`
  - `python -m compileall app tests`
  - `npm run build` from `frontend`
  - `python -m pytest -q`

## Deployment Status

This file does not confirm that Vercel or Render has deployed the latest commit. It is a checklist for verifying deployment after a push.

### Frontend

Expected Vercel project settings:

```text
Project: mitrabooks-erp-staging or production MitraBooks project
Root directory: frontend
Build command: npm run build
Output directory: build
```

Do not set the root directory to `frontend/mitrabooks-erp`. That folder is copied into the final build output by `frontend/scripts/build.js` and depends on sibling `assets` and `shared` folders.

### URLs To Verify

```text
Staging: https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
Production: https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

## Post-Push Checklist

- [ ] GitHub push completed.
- [ ] Vercel deployment triggered for the intended branch.
- [ ] Vercel build completed successfully.
- [ ] Custom domain resolves to the intended Vercel project.
- [ ] `/mitrabooks-erp/landing.html` loads.
- [ ] About, Contact, Privacy Policy, and Terms of Use pages load.
- [ ] Existing login page remains reachable.
- [ ] MitraBooks ERP shell loads after login.
- [ ] Backend pricing endpoint returns the MitraBooks Free, Basic, Starter, and Growth plans.

## Known Non-Blocking Warnings

The frontend build currently completes with existing ESLint warnings in unrelated React files, including unused imports and missing hook dependencies. These warnings should be cleaned up separately, but they did not block the current build.

## Security Check

Before any deployment promotion:

- Do not commit `.env`, `.vercel`, secrets, tokens, database dumps, or production exports.
- Ensure staging data is separate from production data.
- Verify the frontend points to the intended backend environment.
