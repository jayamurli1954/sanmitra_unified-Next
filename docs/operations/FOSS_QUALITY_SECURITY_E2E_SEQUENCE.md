# FOSS Quality, Security, and E2E Testing Sequence

## Purpose

This runbook combines the FOSS tools from `D:\Documents\Complete_e2e_testing_guide.txt` into a SanMitra-safe validation sequence:

- Playwright for browser E2E and smoke workflows.
- SonarQube Community Edition for source code quality and maintainability analysis.
- OWASP ZAP for dynamic application security testing against a running test target.
- Trivy for dependency, secret, filesystem, and misconfiguration scanning.

The goal is not one giant test that blocks all work. The goal is a repeatable staged pipeline that catches issues at the right layer without attacking production tenants or creating accounting/test-data risk.

## Current State

Already present in this repository:

- `backend-ci` GitHub Actions workflow with repository safety, Python compile checks, text integrity checks, frontend/backend route contract checks, and focused pytest.
- `codeql-analysis` GitHub Actions workflow for Python static security and quality analysis.
- `security-trivy` GitHub Actions workflow for filesystem scanning with `vuln`, `secret`, and `misconfig` scanners.
- `mandir-stability-gate` GitHub Actions workflow for focused MandirMitra/accounting regression tests.
- Frontend package scripts include Playwright-related commands, but no committed Playwright config or E2E test suite was found.

Not yet present:

- SonarQube project configuration.
- SonarQube server/token setup.
- OWASP ZAP workflow/configuration.
- A local container or compose stack for isolated full-stack browser and ZAP testing.

Initial Playwright foundation added after this runbook:

- `frontend/playwright.config.js`
- `frontend/e2e/global-smoke.spec.js`
- `frontend/e2e/authenticated-smoke.spec.js`
- `.github/workflows/global-e2e-playwright.yml`

The first workflow is manual and accepts a `base_url` input. Use the URL that serves the React app shell for the target environment. At the time of setup, `https://mitrabooks-erp.vercel.app` served the unified frontend app shell, while `https://mandirmitra.sanmitratech.in` resolved to a SanMitra corporate page in Playwright and was therefore not a valid E2E target for this suite.

## Target State

SanMitra should use a layered validation sequence:

1. Static and repository checks.
2. Unit/API/regression tests.
3. Dependency and secret scanning.
4. Optional SonarQube quality gate.
5. Deploy or boot an isolated staging/test app.
6. Playwright E2E smoke tests against demo tenants only.
7. OWASP ZAP baseline scan against the same isolated target.
8. Manual review of reports before production release.

## Recommended Sequence

### Phase 1: Repository Safety and Static Checks

Run first because these are fast and do not need a running app.

Current commands:

```powershell
python scripts/check_repository_safety.py
python -m compileall app scripts tests
python scripts/check_text_integrity.py app scripts .github/workflows
python scripts/check_frontend_backend_route_contract.py --fail-on-missing
```

CI owner:

- Existing `backend-ci`.

Gate:

- Must pass before any staging deployment.

### Phase 2: Unit, API, and Mandir Regression Tests

Run backend tests that protect tenant isolation, app-key isolation, accounting invariants, receipts, and MandirMitra behavior.

Current CI owner:

- Existing `backend-ci`.
- Existing `mandir-stability-gate`.

Gate:

- Must pass before E2E browser testing is considered meaningful.

### Phase 3: Dependency, Secret, and Misconfiguration Scan

Run Trivy against the repository.

Current CI owner:

- Existing `security-trivy`.

Current behavior:

- Uploads SARIF results.
- Does not fail the build yet because `exit-code: "0"` is configured.

Recommended next step:

- Keep non-blocking while MandirMitra stabilization continues.
- Later change to blocking for `CRITICAL` issues after a baseline cleanup.

Gate:

- For production releases, manually review HIGH/CRITICAL findings until the workflow becomes blocking.

### Phase 4: Static Code Quality with SonarQube CE

SonarQube Community Edition can be added as an additional quality dashboard, not as a replacement for CodeQL or tests.

Required setup:

- A running SonarQube CE server.
- GitHub Actions secrets:
  - `SONAR_TOKEN`
  - `SONAR_HOST_URL`
- A repo-root `sonar-project.properties`.

Suggested first configuration:

```properties
sonar.projectKey=sanmitra-unified-next
sonar.projectName=SanMitra Unified Next
sonar.sources=app,scripts,frontend/src,tests
sonar.exclusions=**/node_modules/**,**/build/**,**/.venv/**,**/venv/**,**/.pytest_cache/**,**/htmlcov/**,**/tmp/**
sonar.python.version=3.11
```

Recommended rollout:

1. Run SonarQube manually first.
2. Add a manual GitHub Actions workflow.
3. Make it scheduled/non-blocking.
4. Only later consider a blocking quality gate.

Gate:

- Initially advisory only.

### Phase 5: Isolated Staging/Test Deployment

Playwright and ZAP need a running application.

Safe targets:

- Local full-stack app with seeded demo tenants.
- Staging deployment with only demo/test tenants.

Unsafe targets:

- Production tenants.
- Real tenant data.
- Any environment where ZAP active scan could mutate business data.

Gate:

- Confirm the test target has demo tenants only, or use read-only smoke paths.

### Phase 6: Playwright E2E Smoke

Playwright should run before ZAP because it proves the app is usable and can also create authenticated session state for later security testing.

Initial MandirMitra browser smoke should cover:

- Login.
- Tenant switch between demo tenants.
- Dashboard loads.
- Devotee mobile lookup stays tenant-scoped.
- Donation creation in a demo tenant.
- Receipt PDF download.
- Seva booking in a demo tenant.
- Trial Balance opens and balances.
- Ledger drilldown opens voucher detail.
- Quick Expense rejects negative cash postings.

Rules:

- Use demo tenants only.
- Do not run destructive tests on real tenants.
- Do not edit/delete posted accounting entries; test reversals only.
- Store Playwright traces/screenshots as artifacts.

Gate:

- Must pass before ZAP is meaningful.

### Phase 7: OWASP ZAP Baseline Scan

Start with ZAP baseline/passive scanning only.

Recommended first command shape:

```powershell
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://staging-demo-url.example -r zap-baseline-report.html
```

Recommended CI behavior:

- `workflow_dispatch` only at first.
- Run against staging/demo target.
- Upload HTML/XML reports as artifacts.
- Do not run active scan in production.
- Do not fail the build until findings are triaged and a rules baseline exists.

Gate:

- Manual review of alerts.
- Block production only for confirmed high-risk findings after baseline triage.

### Phase 8: Consolidated Release Decision

A production release should require:

- `backend-ci`: pass.
- `mandir-stability-gate`: pass when Mandir/accounting code changed.
- `security-trivy`: reviewed, later blocking for criticals.
- `codeql-analysis`: reviewed.
- SonarQube: reviewed once configured.
- Playwright smoke: pass against staging/demo.
- ZAP baseline: reviewed against staging/demo.
- Backup/restore and rollback notes current.

## Suggested GitHub Actions Shape

Keep the current workflows. Add only after manual/local proof:

1. `sonarqube.yml`
   - Manual and scheduled initially.
   - Requires `SONAR_TOKEN` and `SONAR_HOST_URL`.

2. `mandir-e2e-playwright.yml`
   - Manual initially.
   - Uses staging/demo URL or local test stack.
   - Uploads Playwright report.

3. `zap-baseline.yml`
   - Manual initially.
   - Depends on a safe staging/demo URL.
   - Uploads ZAP report.
   - Non-blocking until triaged.

Do not combine all three into one blocking workflow immediately. Separate workflows keep failures understandable for one maintainer.

## Gap

Before this can become fully automated, SanMitra needs:

- A committed Playwright config and first MandirMitra smoke suite.
- A defined test user and demo tenant policy.
- A staging URL and test data reset process.
- SonarQube server ownership and retention policy.
- ZAP rules baseline after first scan triage.
- A decision on when Trivy/Sonar/ZAP become blocking.

## Non-Goals

- Do not run ZAP active scans against production.
- Do not use real tenant data for destructive E2E tests.
- Do not make SonarQube a hard gate before the initial issue baseline is known.
- Do not replace accounting invariant tests with browser tests.
- Do not combine all products into one E2E pass before the staged E2E plan is green.
