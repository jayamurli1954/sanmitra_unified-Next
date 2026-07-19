# Large-File Modularization Plan & Safety Protocol

Status: proposed (foundation / non-behavioral refactor)
Owner: platform maintainer
Scope: split oversized source files into smaller cohesive modules WITHOUT changing behavior, while four product frontends are live (including a live MandirMitra client).

This document is the binding protocol for the file-splitting effort. Every step in the
effort must comply with the rules here. If a proposed change cannot satisfy these rules,
it is out of scope for this effort and must be handled separately.

---

## 1. Current state

A code review found 30+ source files over 1,000 lines. Verified real line counts:

| File | Real lines |
| --- | --- |
| `frontend/mitrabooks-erp/app.js` | ~20,344 |
| `app/modules/mandir_compat/router.py` | ~12,175 |
| `frontend/shared/app-shell.css` | ~6,166 |
| `app/modules/housing_compat/router.py` | ~5,477 |
| `app/modules/business/service.py` | ~5,236 |
| `frontend/gruhamitra/src/screens/SettingsScreen.jsx` | ~4,694 |
| `frontend/mitrabooks-erp/index.css` | ~4,652 |
| `app/modules/business/router.py` | ~4,251 |
| `app/accounting/service.py` | ~2,539 |
| 19+ more | 1,000–2,162 each |

Most of these files are already internally organized with section banners
(`// SECTION:`, `# SECTION:`, `# ===== =====`) or self-contained components (`*Tab`),
so natural split seams already exist.

## 2. Target state

- No source file over ~1,500 lines.
- Zero files over 3,000 lines.
- Typical file 300–900 lines: small enough to read and reason about in one sitting.
- A CI/preflight guard prevents new oversized files from appearing.

Total repository line count is expected to stay roughly flat (a small increase from
import/export boilerplate). This effort redistributes code; it does not remove features.

## 3. Gap

- No enforced file-size ceiling; files drift larger with every feature.
- Product-specific code lives inside "shared" files (e.g. a ~3,970-line LegalMitra block
  inside `frontend/shared/app-shell.css`).
- `frontend/mitrabooks-erp` has no bundler, so `app.js` cannot fail-fast at build time —
  a wiring mistake there surfaces at runtime, not compile time.

---

## 4. Non-negotiable safety principles

1. **Pure move-and-re-import only.** A diff may only change *where code lives* and *how it
   is imported/exported*. It must NOT change logic, API request/response shapes,
   calculations, SQL/Mongo queries, tenant scoping, or accounting behavior. If a diff
   changes anything other than location + imports, it is not part of this effort.
2. **One file (seam) at a time, one small commit at a time.** No big-bang refactor. Each
   commit is small enough to review by eye and to revert instantly.
3. **`python scripts/preflight.py` must be green before every push** (AGENTS.md §28). Red
   preflight = do not push. For frontend changes, also run `--frontend`.
4. **Nothing auto-deploys.** Production is reached only via reviewed release tags + manual
   `render-deploy` (AGENTS.md §27). A bad commit sits in git, never in front of a client,
   until an explicit deploy.
5. **Quarantine the accounting/financial core.** See §6. Those files/functions are not
   part of mechanical splitting.
6. **Rollback path is always a plain `git revert`** of the small commit. Because no data,
   schema, or ledger is touched, rollback is trivial and side-effect-free.

---

## 5. Risk tiers (ordered by how loudly a mistake announces itself)

We split in this order so mistakes are caught *before* production wherever possible.

| Tier | Category | Why | Safety net |
| --- | --- | --- | --- |
| 1 | Python backend (`business`, `mandir_compat`, `housing_compat`, non-posting parts of `accounting`) | Missing import fails loudly | `compileall` + pytest + route contract in preflight |
| 1 | React w/ bundler (`SettingsScreen.jsx`, GruhaMitra/Vite) | Build fails on bad import | Vite build + Playwright smoke |
| 1 | CSS (`app-shell.css`, `index.css`) | No logic; only load-order matters | Visual smoke; keep load order identical |
| 2 | `frontend/mitrabooks-erp/app.js` | No bundler → runtime-only failure mode | Manual + Playwright click-through of affected screens |
| 3 | Accounting posting core / donation-receipt posting | Financial + live-client risk | QUARANTINED — not in this effort (see §6) |

---

## 6. Quarantine list (do NOT touch as part of mechanical splitting)

Per AGENTS.md §10 accounting doctrine and the live MandirMitra client:

- `app/accounting/service.py`: `post_journal_entry`, `reverse_journal_entry`, and the
  debit=credit / atomicity / idempotency validation around them. (The *read/report*
  functions — trial balance, P&L, balance sheet, AR/AP — MAY be extracted; the posting
  core stays put.)
- `app/modules/mandir_compat` donation/seva/receipt POSTING helpers and receipt-number
  sequencing. (The PDF *rendering* subsystem MAY be extracted; the posting/sequence logic
  stays put.)
- `app/modules/business/service.py` compensation/rollback helpers and voucher-number
  reservation — extract only into a shared helper module with byte-identical logic, or
  leave in place if extraction risks the invariant.

Any change to quarantined code is a separate, deliberately-reviewed task with its own
tests — never bundled into a "just moving files" commit.

---

## 7. Per-file target breakdown (projected)

Total lines stay ~flat; the point is the drop in *max file size*.

| File | Before | After (largest child) | Approx child files |
| --- | --- | --- | --- |
| `mitrabooks-erp/app.js` | 20,344 | ~1,000–1,500 | 15–20 (core, workspaces/*, documents/*, gst/*, vouchers/*, events) |
| `mandir_compat/router.py` | 12,175 | ~1,500 (PDF engine) | ~10 (receipts, routers/*, helpers/*) |
| `business/service.py` | 5,236 | ~1,100 | ~12 (services/* per GST/document domain + _helpers) |
| `housing_compat/router.py` | 5,477 | ~1,000 | ~10 (maintenance, messaging, meetings, assets, pdf + routes) |
| `business/router.py` | 4,251 | ~500 | ~14 (routers/* per URL group) |
| `SettingsScreen.jsx` | 4,694 | ~1,180 (FlatsBlocksTab) | 18 (one per *Tab + shell) |
| `accounting/service.py` | 2,539 | ~950 (reports) | ~4 (reports, coa_mapping, chart, posting-core stays) |
| `app-shell.css` | 6,166 | shell ~2,200 | + `legalmitra.css` ~3,970 |
| `index.css` | 4,652 | ~1,500 | dashboards/widgets + reports split |

Headline: largest file 20,344 → ~1,500 (~93% reduction in worst-case file size);
files over 1,500 lines: ~15 → 0–2.

---

## 8. Execution sequence (phased)

Each phase is independently shippable and revertible.

**Phase 0 — Guardrail (this doc + line-count check).** Add a file-size check to
`scripts/preflight.py` (warn ≥800, fail ≥1,500 for new/changed source files;
grandfather the existing offenders on an explicit allowlist that shrinks as we split).
This stops the problem getting worse while we work. Zero application code touched.

**Phase 1 — Mechanical, lowest risk (pilot first).**
1. `SettingsScreen.jsx` → 18 files (pilot; proves the pattern).
2. `app-shell.css` → extract the LegalMitra block to `legalmitra.css`.
3. `business/service.py` → `services/*` by banner.
4. `mandir_compat/router.py` helpers + PDF subsystem → modules (NOT posting helpers).

**Phase 2 — Backend routers.**
5. `business/router.py` → router package.
6. `housing_compat/router.py` → introduce seams, then split.
7. `accounting/service.py` → extract `reports.py` / `coa_mapping.py` / `chart.py`
   (posting core stays).

**Phase 3 — `app.js` (most care, done last).**
8. Split section-by-section into a module graph; untangle the shared event dispatcher by
   having each module register its own handlers. Verify each chunk with a browser
   click-through of the affected MandirMitra/MitraBooks screens before deploy.

**Phase 4 — Remaining 1,000–2,162 line files**, opportunistically as they are touched.

Do not start a later phase until the previous one's commits are green in preflight and,
where relevant, verified in a smoke check.

---

## 9. Per-step acceptance checklist

Before committing any split step:

- [ ] Diff is pure move + import/export only (no logic/behavior change).
- [ ] No quarantined code (§6) was modified.
- [ ] `python scripts/preflight.py` is green (add `--frontend` for frontend changes).
- [ ] For `app.js` steps: affected screens click-tested (manual or Playwright).
- [ ] Commit is small, single-purpose, and has a clear revert.
- [ ] Tenant isolation, app-key/module access, and accounting invariants are unchanged
      (they must be, since logic did not change) — confirm no query/scope was altered.

---

## 10. Non-goals

- No feature changes, no bug fixes bundled into split commits.
- No accounting-engine rewrite; posting core stays intact.
- No frontend framework migration (introducing Vite for `mitrabooks-erp` is a *separate*
  decision, not assumed by this plan).
- No database, schema, migration, or ledger changes.
- No change to public API contracts.
- InvestMitra remains out of unified scope (AGENTS.md §14).

---

## 10a. Findings & adjustments (discovered during execution)

**2026-07-18 — Phase 1, item 1 (`SettingsScreen.jsx`): DONE.**
Split 4,693 → 130 lines; 16 tab modules + `settingsHelpers.js` under
`frontend/gruhamitra/src/screens/settings/`. Verified by a clean `vite build`.
Largest child `FlatsBlocksTab.jsx` (~1,191, under the 1,500 limit).

**2026-07-18 — Phase 1, item 2 (`app-shell.css` LegalMitra block): DEFERRED.**
Investigation showed the `.legal-*` block is NOT LegalMitra-only. It is shared
cross-product CSS:
- `frontend/mandir-public/*` and `frontend/public/*` (LIVE MandirMitra marketing
  pages) reuse `.legal-editorial-page`, `.legal-navbar`, `.legal-info-grid`,
  `.legal-footer`, `.legal-contact-page`, etc. — they override only colors inline and
  rely on the base layout from `app-shell.css`.
- `frontend/shared/pwa-shell.js` (runs on EVERY page) uses `.legal-install-suggestion`
  / `.legal-install-actions` for the PWA install prompt.
- The block's responsive rules are interleaved in a shared `@media` block
  (lines 5975–6131), after the base block (1827–5800).

Extracting to a `legalmitra.css` linked only on LegalMitra pages would break live
MandirMitra pages and the install prompt platform-wide. A behavior-preserving move is
possible only by loading the extracted file on ALL ~24 pages that load `app-shell.css`,
in the correct order (immediately after `app-shell.css`, before per-page inline
`<style>` overrides). That is a larger, live-surface change than a first CSS split
should be. DEFERRED pending an explicit decision; if pursued, the file should be named
for its real role (shared editorial/marketing CSS), not `legalmitra.css`.

Lesson for CSS splits: verify class-usage ACROSS all products before assuming a block is
product-specific; a `.legal-*` (or any) prefix does not guarantee single-product scope.

## 11. Rollback

Every step is a small commit that only moves code. If anything looks wrong:

1. `git revert <commit>` the offending split step (no data/schema involved).
2. Re-run `python scripts/preflight.py` to confirm green.
3. Nothing to migrate or reverse in the database or ledger, because none were touched.
