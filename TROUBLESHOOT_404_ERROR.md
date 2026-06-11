# Troubleshooting 404 Or Wrong App On MitraBooks Deployment

## Symptom

One of these occurs:

- `https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/` returns 404.
- The custom domain serves another SanMitra app.
- The root URL works but `/mitrabooks-erp/` fails.

## Most Likely Causes

1. The custom domain is attached to the wrong Vercel project.
2. Vercel root directory is set to `frontend/mitrabooks-erp` instead of `frontend`.
3. The output directory is not `build`.
4. The route rewrite for `/mitrabooks-erp/` is missing or stale.
5. The local Vercel CLI link points at the wrong project.

## Required Vercel Settings

```text
Project: MitraBooks staging or production project
Root directory: frontend
Build command: npm run build
Output directory: build
Custom domain: staging.mitrabooks.sanmitratech.in or production domain
```

## URL Checks

Test these in order:

```text
https://mitrabooks-erp-staging.vercel.app/
https://mitrabooks-erp-staging.vercel.app/mitrabooks-erp/
https://staging.mitrabooks.sanmitratech.in/
https://staging.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

If the Vercel direct URL works but the custom domain fails, check DNS and Vercel domain attachment.

If root works but `/mitrabooks-erp/` fails, check route rewrites and static build output.

If both fail, check the build logs and project root settings.

## Local CLI Check

From `frontend`, inspect the local Vercel project link:

```powershell
Get-Content .vercel\project.json
```

Do not commit `.vercel`. The MitraBooks static app has a local `.gitignore` entry for that directory.
