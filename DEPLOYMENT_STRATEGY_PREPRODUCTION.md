# Pre-Production To Production Deployment Strategy

## Objective

Use a staging/pre-production environment for MitraBooks validation before production promotion.

## Current State

- MitraBooks frontend is built from `frontend`.
- The MitraBooks ERP static app is served under `/mitrabooks-erp/`.
- The backend is FastAPI in this repository.
- Production and staging deployment verification must be done through the hosting dashboards after each push.

## Recommended Strategy

Use a dedicated Vercel staging project for stakeholder testing and E2E validation.

```text
Staging frontend: staging.mitrabooks.sanmitratech.in
Production frontend: www.mitrabooks.sanmitratech.in
Staging backend: staging Render service
Production backend: production Render service
```

## Vercel Project Settings

```text
Root directory: frontend
Build command: npm run build
Output directory: build
Framework: Create React App / static build
```

The root directory must be `frontend`, not `frontend/mitrabooks-erp`.

## Branch Model

```text
feature branch -> PR / review -> staging validation -> main -> production deployment
```

If a separate `develop` branch is used later, document that explicitly in the release notes for that deployment. Do not assume `develop` is active unless the project settings confirm it.

## Promotion Checklist

- [ ] Full Python test suite passes.
- [ ] Frontend build passes.
- [ ] MitraBooks smoke test passes on staging.
- [ ] Landing page, legal pages, and login route load.
- [ ] Accounting-critical workflows pass the staged E2E checklist.
- [ ] No secrets, `.env`, `.vercel`, dumps, or PII exports are committed.
- [ ] Rollback target is known.

## Rollback

Frontend rollback should use Vercel's previous deployment rollback. Backend rollback should use the previous known-good release tag or deployment version.

Do not roll back financial data by editing ledger rows. Use reversal or adjustment entries for accounting corrections.
