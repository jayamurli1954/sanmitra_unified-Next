# Security Remediation PR Plan

Date: 2026-07-08  
Source review: [`docs/operations/Code_Review-Sanmitra_Unified-Next.docx`](../operations/Code_Review-Sanmitra_Unified-Next.docx) (2026-07-05 static review)  
Status tracker: [`docs/operations/MITRABOOKS_PENDING_GAP_TODO.md`](../operations/MITRABOOKS_PENDING_GAP_TODO.md) — **Security P0/P1/P2**  
Accounting cross-store note: [`MITRABOOKS_REVIEW_2026-06-26.md`](MITRABOOKS_REVIEW_2026-06-26.md) — `SEC-P0-00`

Each PR should be reviewable in one sitting, independently mergeable where noted, and covered by tests before merge. Run `python scripts/preflight.py` (and `--frontend` when UI changes) before push.

## PR index

| PR | Title | Severity | Size | Ship alone? | Depends on |
| --- | --- | --- | --- | --- | --- |
| PR1 | Strip secrets from `/users/me` | Critical | S | Yes | — |
| PR2 | Harden open registration | Critical | M | Yes (coordinate Gruha frontend) | — |
| PR3 | OTP/Google tenant assignment policy | Critical | M | No | PR2 |
| PR4 | Auth endpoint rate limiting | High | S–M | Yes | — |
| PR5 | Mandir public payment + autofill | Critical/High | M | Yes | — |
| PR6 | Mandir onboarding secret in prod | Critical | S | Yes | — |
| PR7 | Gate Legal Tavily web-search routes | High | S | Yes | PR4 pattern |
| PR8 | Mandir compat RBAC baseline | High | L | Partial (8a writes first) | PR5, PR6 |
| PR9 | Gruha compat RBAC baseline | High | L | Partial | PR8 pattern |
| PR10 | MitraBooks compat RBAC baseline | High | M | Yes | PR8 pattern |
| PR11 | Upload caps + production surface hardening | High/Medium | M | Yes | PR2 (password policy) |
| PR12 | Frontend token storage + CSP | High | L | Separate track | API auth stable |
| PR13 | Ops/scripts + default credential cleanup | Critical (ops) | S | Yes | — |

`SEC-P0-00` (cross-store posting boundary) is tracked separately in the pending gap tracker; close it with explicit compensation tests before production signoff.

## Merge batches

| Batch | PRs | Target |
| --- | --- | --- |
| 1 — Critical closures | PR1, PR2 (+ Gruha frontend), PR3, PR5, PR6, PR13 | Week 1 |
| 2 — Abuse prevention | PR4, PR7 | Week 1–2 |
| 3 — Authorization depth | PR8a → PR9a → PR10 → PR8b/9b | Week 2–4 |
| 4 — Hardening + frontend | PR11, PR12 | Week 4+ |

## PR summaries

### PR1 — `/users/me` response allow-list

- **Files:** `app/core/users/router.py`, `tests/test_users_me_context.py`
- **Change:** Stop spreading Mongo `user_doc`; exclude `hashed_password` and internal fields.
- **Accept:** Response never contains `hashed_password`; preflight passes.

### PR2 — Registration hardening

- **Files:** `app/core/auth/router.py`, `app/api/legacy_alias_router.py`, `app/core/users/service.py`, `app/config.py`, `frontend/gruhamitra/src/services/authService.js`
- **Change:** Reject open `role`/`tenant_id` on public register; prod gate via `ALLOW_OPEN_REGISTRATION` or equivalent; role allow-list in `create_user()`.
- **Accept:** Unauthenticated caller cannot create admin roles or join arbitrary tenants.

### PR3 — OTP/Google first-login tenant policy

- **Files:** `app/core/auth/service.py`, `app/core/auth/router.py`, onboarding/invite validation
- **Change:** New users require invite, join-request, or pre-provisioned membership — not bare `tenant_id` in body.
- **Accept:** No new user in tenant without approved onboarding path.

### PR4 — Auth rate limits

- **Files:** `app/core/auth/router.py`, `app/core/rate_limiting.py`, tests
- **Change:** `@limiter.limit` on login, register, forgot/reset, OTP send/verify.
- **Accept:** Abuse returns `429`; E2E not broken in test env.

### PR5 — Mandir public endpoints

- **Files:** `app/modules/mandir_compat/router.py`, `frontend/src/pages/PublicSevaPayment.js`, `tests/test_mandir_posting_guardrails.py`
- **Change:** Payment status scoped by `tenant_id`; remove prefix-regex enumeration; minimize devotee autofill PII.
- **Accept:** Cross-tenant payment read blocked; public seva UI still works.

### PR6 — Mandir onboarding secret

- **Files:** `app/modules/mandir_compat/router.py`, `app/config.py`, `tests/test_mandir_onboarding_auth_flow.py`
- **Change:** `Settings.validate()` fails prod startup if `MANDIR_ONBOARDING_SECRET` unset.
- **Accept:** Onboard without token returns `403` when secret configured.

### PR7 — Legal Tavily routes

- **Files:** `app/modules/legal/router.py`, tests
- **Change:** `get_current_user` + `require_enabled_module("legal")` + rate limit on `/news`, `/judgements`, `/web-search-rag`.
- **Accept:** Unauthenticated calls get `401`; disabled module gets `403`.

### PR8–PR10 — Compat RBAC

- **Files:** `mandir_compat`, `housing_compat`, `mitrabooks_compat` routers; `require_enabled_module`, `require_roles`
- **Change:** Router-level or per-route gates on write/financial/admin paths first.
- **Accept:** `viewer` cannot post donations, verify payments, or run billing close.

### PR11 — Production surface + uploads

- **Files:** `housing_compat/router.py`, `app/main.py`, `app/core/auth/schemas.py`, tests
- **Change:** Journal attachment size cap; disable OpenAPI in prod; stronger password policy; generic health errors in prod.
- **Accept:** Oversized upload rejected; `/docs` absent in production.

### PR12 — Frontend token/CSP (separate release)

- **Files:** `frontend/shared/api-client.js`, `frontend/vercel.json`, Playwright smoke
- **Change:** httpOnly cookie strategy or CSP tightening + `innerHTML` audit.
- **Accept:** Documented auth storage; no login regression across shells.

### PR13 — Ops credential cleanup

- **Files:** `scripts/fix_superadmin.py`, `.env.example`, optional `docs/operations/PRODUCTION_SECURITY_CHECKLIST.md`
- **Change:** No hardcoded passwords in scripts; placeholder-only example env.
- **Accept:** Script refuses empty password; example env not copy-paste safe for prod.

## PR description template

```markdown
## Summary
- [Vulnerability class closed]

## Security impact
- Before: ...
- After: ...

## Breaking changes
- [ ] API contract changes
- [ ] Frontend coordination required

## AGENTS.md checklist
- [ ] Tenant isolation
- [ ] Module access / RBAC
- [ ] No secrets committed
- [ ] Tests added
- [ ] `python scripts/preflight.py` passed

## Test plan
- [ ] New security tests: ...
- [ ] Manual: ...
```

## Out of scope (separate workstreams)

- Frontend monolith extraction (`E0`–`E26` in Code Review DOCX)
- `phase1_main.py` removal
- JWT revalidation on every request
- Full RBAC deny-matrix automation
- Dependency CVE triage (Trivy SARIF)
- InvestMitra (excluded from unified scope)

## Residual risk after all PRs

- Within-tenant IDOR on compat routes
- LegalMitra external provider confidentiality for uploaded documents
- Production environment audit (secrets, bootstrap flags) — not replaceable by code-only fixes
