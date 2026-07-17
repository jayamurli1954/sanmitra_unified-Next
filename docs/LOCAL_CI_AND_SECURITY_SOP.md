# Local CI & Security SOP — run the gates before you push

GitHub Actions is the source of truth for validation, but this repo already has
**2500+ workflow runs** and per-commit CI is expensive. The standard operating
procedure is therefore: **run the locally-reproducible gates first, push only when
they are green.** A green local run = a green push, and fewer wasted Actions runs.

> One command does Tier 1: **`python scripts/preflight.py`** (see [scripts/preflight.py](../scripts/preflight.py)).
> This is mandated by [AGENTS.md](../AGENTS.md) §28 — do not bypass it.

---

## Agent destructive command guardrails

Before running shell commands (especially git, filesystem delete, database admin, deploy,
or destructive E2E), follow [AGENTS.md](../AGENTS.md) **§5 Agent Shell Command Guardrails**.

This repo does **not** require the external `destructive_command_guard` (dcg) tool; the
AGENTS policy is the source of truth. Blocked patterns include force-push to shared
branches, hard reset/clean, unscoped DB drops/truncates, posted-ledger edits, production
deploys without approval, and destructive demo runs against non-demo tenants.

If a command is blocked: stop, explain risk, propose a safe alternative, and wait for
explicit user approval.

---

## The three tiers

### Tier 1 — Backend gate (ALWAYS, zero install)

Reproduces the `backend-ci` and `accounting-stability-gate` workflows exactly.

```bash
python scripts/preflight.py            # full pytest
python scripts/preflight.py --quick    # faster pytest subset for tight loops
```

Equivalent raw commands (what the script runs):

```bash
python scripts/check_repository_safety.py
python scripts/check_agents_compliance.py
python -m compileall app scripts tests
python scripts/check_text_integrity.py app scripts .github/workflows
python scripts/check_frontend_backend_route_contract.py --fail-on-missing
python -m pytest -q
```

If Tier 1 is green, `backend-ci` and `accounting-stability-gate` will pass.

### Tier 2 — Frontend smoke (only when `frontend/**` changed)

Reproduces `mitrabooks-shell-smoke` and `global-e2e-playwright`. Needs Node and the
Playwright Chromium browser (`cd frontend && npx playwright install chromium` once).

```bash
python scripts/preflight.py --frontend
```

The script serves the frontends (`scripts/serve_frontends.py` on 127.0.0.1:3300) and
runs the smoke specs, then tears the server down. Raw equivalent:

```bash
cd frontend
python ../scripts/serve_frontends.py --host 127.0.0.1 --port 3300 &
npx playwright test e2e/global-smoke.spec.js --project=chromium
npx playwright test e2e/mitrabooks-shell.spec.js --project=chromium --timeout=90000
```

### Tier 3 — Security scanners (`codeql` / `security-trivy` / `semgrep`)

```bash
python scripts/preflight.py --security    # best-effort: runs each scanner that is installed
```

Local feasibility is uneven — be honest about it:

| Scanner | What it does | Local on Windows | How |
| --- | --- | --- | --- |
| **trivy** | dependency vulns, secrets, misconfig | ✅ installable | install the Windows binary, then `trivy fs . --severity HIGH,CRITICAL --scanners vuln,secret,misconfig` |
| **semgrep** | Python/JS/secret SAST | ⚠️ no native Windows | Docker or WSL only; otherwise relies on the `semgrep` CI job |
| **codeql** | deep Python security analysis | ❌ impractical | CI-only (runs on schedule + push); needs the CodeQL CLI + a DB build |

**Because `semgrep` and `codeql` cannot be reliably preflighted on Windows, they are
CI-only gates.** `preflight.py --security` runs whichever scanners are present and
clearly prints `SKIPPED` for the rest — it never silently passes a scanner that did
not run.

---

## SOP per change type

| Change | Preflight before pushing |
| --- | --- |
| Backend feature / bug fix | `python scripts/preflight.py` |
| Frontend change (`frontend/**`) | `python scripts/preflight.py --frontend` |
| Dependency / lockfile change | `python scripts/preflight.py --security` (so trivy catches new CVEs) |
| Everything before a release | `python scripts/preflight.py --all`, then `scripts/release_preflight.py` |

Per the commit-grouping policy: build and preflight a whole feature locally, then
push it as **one** grouped commit. Bug fixes for already-live features get their own
preflighted commit. Fewer pushes = fewer Actions runs.

---

## What you cannot reproduce locally (and that is OK)

`semgrep` and `codeql` run in CI only. The mitigation is to keep them off every-branch
pushes where possible and rely on their PR + scheduled runs — track that as a CI-config
follow-up. Everything else (backend gate + frontend smoke + trivy) is preflightable, so
those should never be the reason a push goes red.
