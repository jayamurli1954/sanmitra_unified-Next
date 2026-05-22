# Release and Rollback Runbook

This runbook defines the minimum release discipline for the SanMitra unified backend.

## Version Format

The backend version is stored in `VERSION`.

Use semantic versioning:

- `MAJOR`: breaking API, schema, or migration behavior.
- `MINOR`: backward-compatible feature additions.
- `PATCH`: bug fixes, guardrails, documentation, and test-only changes.

Production release tags must use:

```text
backend-vMAJOR.MINOR.PATCH
```

Example:

```text
backend-v1.2.3
```

## Required Checks Before Release

Before a release tag is created, GitHub Actions must pass:

- Repository safety guardrails.
- Python compile check.
- Text integrity check.
- Frontend/backend route contract check.
- Focused release preflight tests.

The `release-tag` workflow runs these checks before it creates the tag.

Bootstrap CI currently runs the supported foundation test suite explicitly. Some copied legacy tests still reference old `modules.*` import paths and are not part of the active gate until they are migrated or removed. Receipt PDF rendering tests are also excluded from the bootstrap gate until the rendering stack is validated consistently in CI.

## Code Scanning Bootstrap

`codeql-analysis` and `security-trivy` run on GitHub Actions. During repository bootstrap, SARIF upload can be non-blocking until GitHub code scanning is enabled for the repository.

Enable it in GitHub:

```text
Settings -> Code security and analysis -> Code scanning
```

After code scanning is enabled and stable, the SARIF upload steps can be changed back to blocking gates if desired.

## Release Flow

1. Merge the reviewed PR into `main`.
2. Update `VERSION` in a dedicated version bump commit.
3. Run the GitHub Actions workflow: `release-tag`.
4. Provide the exact `VERSION` value and short release notes.
5. Confirm the created tag, for example `backend-v1.2.3`.
6. Run `render-deploy` for `staging`.
7. Verify staging health and critical accounting workflows.
8. Run `render-deploy` for `production` with the same version tag.

Production deploy must always reference a version tag.

## MandirMitra First-Live Candidate

The MandirMitra first-live backend candidate should use a reviewed production release tag after CI passes.

Recommended candidate version:

```text
backend-v1.3.0
```

Use this as the first MandirMitra production candidate only after:

- The `VERSION` file is updated to `1.3.0`.
- GitHub CI, CodeQL, Trivy, and release preflight are green.
- The `release-tag` workflow creates `backend-v1.3.0`.
- Staging is deployed and smoke-tested with non-destructive checks or a demo/test tenant.
- Production deploy is manually triggered with `version_tag=backend-v1.3.0`.

## Rollback Rule

Rollback means returning production to the last known good `backend-v*` tag. Do not roll back by guessing a branch head.

Preferred rollback target:

```text
previous backend-vMAJOR.MINOR.PATCH tag that passed production verification
```

## Rollback Flow

1. Identify the last known good `backend-v*` tag in GitHub.
2. Confirm whether any database migration from the bad release is irreversible.
3. If migrations are safe, redeploy the previous tag through the deployment provider.
4. If migrations are not safe, pause production writes and prepare a forward fix.
5. Record the incident, failed tag, rollback tag, and verification result.

Financial ledger data must not be manually edited during rollback. Corrections must use reversal or adjustment entries.

## Tag Selection

Use these commands locally when needed:

```powershell
git fetch --tags
git tag --list "backend-v*" --sort=-creatordate
git show backend-v1.2.3
```

## GitHub Secrets Required

Render deploy workflow expects:

- `RENDER_STAGING_DEPLOY_HOOK`
- `RENDER_PRODUCTION_DEPLOY_HOOK`

Production environment should require manual approval in GitHub Environments.
