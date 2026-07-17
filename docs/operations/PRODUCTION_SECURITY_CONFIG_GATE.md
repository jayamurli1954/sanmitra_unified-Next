# Production Security Configuration Gate

## Current state

Application startup rejects production when required authentication secrets are missing,
debug token/OTP response controls are enabled, open registration is enabled, or any
super-admin/demo bootstrap and demo E2E seed control is enabled. The local verifier adds
explicit secret-strength and separation checks without printing secret values.

## Target state

Before production release, an authorized operator runs the verifier in the production
service environment and retains only its sanitized JSON evidence. Passing evidence means:

- `ENVIRONMENT` is explicitly `production` or `prod`;
- `JWT_SECRET`, `OTP_PEPPER`, and `MANDIR_ONBOARDING_SECRET` are present, at least 32
  characters, non-placeholder, sufficiently diverse, and mutually distinct;
- all bootstrap, demo seed, auth debug-return, and open-registration controls are
  explicitly `false`.

The verifier never prints or writes secret values. Do not copy production environment
variables into this repository, a shell transcript, CI log, ticket, or signoff document.

## Operator command

Run this inside the authorized production service shell, after configuring its environment:

```powershell
python scripts/verify_production_security_config.py --evidence-output outputs/production-security-config.json
```

The output path must be a JSON file inside this workspace. Review the JSON before retaining
it. A non-zero exit blocks release. Do not use CLI arguments for secrets because process
arguments may be logged.

## Gap

Local tests prove the fail-closed policy and sanitized evidence contract. They do not prove
that the hosted production service has the intended values. Production readiness remains
open until an authorized operator runs the command in the actual service environment and
records fresh passing evidence.

## Platform waiver (2026-07-17) — Path B

**Decision (platform owner):** Keep `ENVIRONMENT=staging` on the live single-stack
service `sanmitra-unified-next-staging-sg` for the time being. Live clients on
LegalMitra, MandirMitra, GruhaMitra, and MitraBooks continue on this service.

**Verified on 2026-07-17 (Render shell):**
`scripts/verify_production_security_config.py` returned `status=blocked` with **only**
`ENVIRONMENT must be explicitly set to production or prod`. All required secrets
passed; all bootstrap, demo seed, open-registration, and auth debug-return controls
were explicitly `false`.

**Sanitized evidence:** `outputs/production-security-config.json` (no secret values).

**What this waiver does not cover:**
- MongoDB Atlas and PostgreSQL backup + isolated restore drills
- `backend-v*` release/rollback tags and clean-worktree machine signoff
- Flipping `ENVIRONMENT` to `production`/`prod` (still required for a full verifier PASS)

**Lift the waiver** by setting `ENVIRONMENT=production` (or `prod`) after a planned
redeploy, confirming `/health`, then re-running the verifier to `status=passed`.

## Implementation sequence

1. Configure secrets through the hosting provider's protected environment controls.
2. Explicitly disable every listed bootstrap, seed, debug-return, and open-registration flag.
3. Run the verifier in the production service shell.
4. Retain only sanitized evidence and feed the confirmation into production signoff.
5. Rotate any secret that was exposed during configuration or verification.

## Non-goals

- This gate does not fetch, rotate, reveal, or persist production secrets.
- It does not contact production from a developer workstation.
- It does not validate backup/restore, release tags, or destructive demo workflows.
