# LegalMitra Staging RAG Verification Runbook

**Status:** operational  
**Product:** LegalMitra  
**Staging API:** `https://sanmitra-unified-next-staging-sg.onrender.com`  
**Related:** `docs/operations/LEGALMITRA_STAGE2_STATUTE_INGEST.md`

## Purpose

Verify staging **corpus** + **retrieval quality** before flipping
`LEGAL_RAG_ENABLED` from `false` → `true` on Render staging.

This is not a production enablement checklist for Claude/`legal_ai`.

## Why `LEGAL_RAG_ENABLED=false` today

Staging intentionally bypasses RAG because:

- `RAG_EMBEDDING_PROVIDER=hash` (weak semantic quality)
- Corpus was historically sparse / noisy on staging

Do not flip the flag until this runbook’s pass criteria succeed.

## Rate-limit lessons (important)

Earlier statute ingest hit **Mongo/Atlas write pressure** and (when embeddings
were enabled) **provider 429s**. Staging verification must stay gentle:

| Do | Don’t |
| --- | --- |
| Ingest **one act at a time** | Bulk-ingest the whole Bare Act folder in one shot |
| Use `--sleep-ms 100` and `--pause-every 25 --pause-seconds 2` | Hammer Atlas with zero delay |
| First pass **without** `--embed` | Enable `--embed` on the first staging load |
| API verify with `--sleep-ms 800+` | Burst `/rag/query` / `/legal-research` |
| Retry after 429 with longer sleep | Keep retrying immediately |

If Atlas or Render returns rate-limit / throttling errors: stop, wait 1–2 minutes,
resume the same command (upserts are safe to re-run).

## Critical tenancy rule

RAG rows are **tenant-scoped**. Ingest must use the same `tenant_id` as the
LegalMitra staging login that will run research.

Default local ingest tenant is `DEMO_LEGAL_TENANT_ID` (`demo-legal-firm`). On staging:

- `seed-tenant-1` is the MandirMitra **TEMPLE** seed — do **not** convert it to LEGAL
  and do **not** ingest LegalMitra RAG into it.
- Use the dedicated LEGAL demo tenant (`demo-legal-firm`, or `demo-legalmitra` if
  that is the staging LegalMitra login tenant) with modules
  `legal`, `rag`, `compliance`, `audit` and app key `legalmitra`.
- Platform owner (`tenant_id=platform`, `organization_type=BUSINESS`) cannot call
  `/api/v1/rag/query` — module gate returns 403.

Confirm the demo LegalMitra user’s `tenant_id` from `/api/v1/auth/me` (or login JWT
claims) and pass `--tenant-id <that-id>` to ingest.

PDF source remains read-only:

```text
D:\sanmitra-backend\data\legal_acts
```

Do not modify that folder.

---

## Step 0 — Preconditions

- Staging API healthy: `GET /health`
- Operator has staging Mongo URI (Render env / secret manager — never commit)
- Operator has LegalMitra staging demo login (email/password)
- Local machine can reach Atlas (IP allowlisted if required)

---

## Step 1 — Corpus check (optional if you know staging is empty)

```powershell
$env:MONGODB_URI = "<staging Mongo URI>"
$env:MONGO_DB_NAME = "<staging db name>"

python scripts/verify_legalmitra_staging_rag.py `
  --mode corpus `
  --tenant-id demo-legal-firm
```

**Pass:** `cgst` ≥ 150, `cgst_rules` ≥ 100, `income_tax_1961` ≥ 400 sections  
**Fail / zeros:** continue to Step 2.

Use the real staging LegalMitra `tenant_id` (`demo-legal-firm` unless `/api/v1/auth/me` shows otherwise).

---

## Step 2 — Rate-limit-safe staging ingest

Point env at staging Mongo only for this session. Ingest one act at a time:

```powershell
$env:MONGODB_URI = "<staging Mongo URI>"
$env:MONGO_DB_NAME = "<staging db name>"

$tenant = "demo-legal-firm"   # confirm against the LegalMitra staging login tenant_id
$pdfDir = "D:\sanmitra-backend\data\legal_acts"

# Part A first (most valuable for GST refund procedure)
python scripts/ingest_structured_statutes.py `
  --pdf-dir $pdfDir `
  --only cgst_rules `
  --tenant-id $tenant `
  --sleep-ms 100 `
  --pause-every 25 `
  --pause-seconds 2

# Then CGST Act
python scripts/ingest_structured_statutes.py `
  --pdf-dir $pdfDir `
  --only cgst `
  --tenant-id $tenant `
  --sleep-ms 100 `
  --pause-every 25 `
  --pause-seconds 2

# Then Income-tax 1961 (largest — expect longer runtime)
python scripts/ingest_structured_statutes.py `
  --pdf-dir $pdfDir `
  --only income_tax_1961 `
  --tenant-id $tenant `
  --sleep-ms 120 `
  --pause-every 20 `
  --pause-seconds 3
```

Notes:

- Omit `--embed` on first load (avoids Gemini/provider 429s). Hash retrieval can
  still work for keyword-heavy statute queries.
- If a run fails mid-act, re-run the same `--only` command; upserts continue safely.
- Optional later: `--embed` only after corpus counts pass, still with sleep/pause.

Re-run Step 1 corpus check.

---

## Step 3 — Retrieval quality via API (`/rag/query`)

Works even while `LEGAL_RAG_ENABLED=false` (legal-research bypasses RAG; this
endpoint still queries the corpus).

```powershell
$env:STAGING_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:E2E_USER_EMAIL = "<staging LegalMitra demo email>"
$env:E2E_USER_PASSWORD = "<staging-only password>"

python scripts/verify_legalmitra_staging_rag.py `
  --mode api `
  --sleep-ms 1000
```

**Pass:**

- GST probe citations mention Section 54 / refund  
- IT probe citations mention Section 139 / return  
- Unrelated contract probe is **not** dominated by GST Section 54 noise  

**Fail on 429:** increase `--sleep-ms` (e.g. 2000) and retry.

---

## Step 4 — Temporary research flip (manual, Dashboard first)

Only after Steps 1–3 pass:

1. Render Dashboard → staging service → Environment  
2. Set `LEGAL_RAG_ENABLED=true` (temporary; do not commit yet)  
3. Restart / redeploy staging  
4. Spot-check 5 questions from `tests/fixtures/legalmitra_gst_s54_eval.json` via
   `/api/v1/legal-research` or LegalMitra UI  

**Pass bar:**

- ≥ 95% GST/IT cases cite retrieved sources or refuse honestly  
- Fabrication / missing-jurisdiction cases still refuse  
- `human_review_required=true` on answers  
- No fabricated sections/case names  

If hash embeddings still inject heavy irrelevant citations → set the flag back to
`false`, keep corpus, and plan embedding-provider upgrade before retrying.

---

## Step 5 — Permanent enable (only after Step 4 pass)

1. Update `render.yaml`: `LEGAL_RAG_ENABLED` → `"true"`  
2. Deploy staging  
3. Re-run `verify_legalmitra_staging_rag.py --mode api`  
4. Record evidence (date, tenant_id, act counts, sample query titles)  

Production enablement is a **separate** gate.

---

## Local Stage 2 engineering gate (offline slice + contract)

Before staging Mongo work, the product contract can be proven locally:

```powershell
python scripts/run_legalmitra_stage2_eval.py --min-grounding 0.95
python -m pytest tests/test_legalmitra_rag_contract.py tests/test_legalmitra_answer_feedback.py -q
```

**Pass criteria:** grounding_rate ≥ 95% (cite or refuse), all contract tests green.

Local statute ingest (no `--embed` first) into workspace Mongo:

```powershell
python scripts/ingest_structured_statutes.py --pdf-dir "D:\sanmitra-backend\data\legal_acts" --only cgst cgst_rules income_tax_1961 --sleep-ms 50 --pause-every 40 --pause-seconds 1
```

Optional later: `--embed` with `RAG_EMBEDDING_PROVIDER=gemini` (requires `GEMINI_API_KEY`).

Staging flag flip (`LEGAL_RAG_ENABLED=true` on Render) still requires this runbook’s Steps 1–5 with the staging LegalMitra `tenant_id`.

---

## Decision table

| Observation | Action |
| --- | --- |
| Corpus counts zero for staging tenant | Rate-limit-safe ingest (Step 2) |
| Corpus OK, `/rag/query` noisy/irrelevant | Keep `LEGAL_RAG_ENABLED=false`; improve embeddings/filters |
| Corpus OK + API probes pass + research spot-check ≥95% | Flip flag permanently (Step 5) |
| Mongo/API 429 during ingest/verify | Stop, wait, increase sleep/pause, resume |

## Safety

- Never commit staging Mongo URIs, passwords, or tokens  
- Never modify `D:\sanmitra-backend\data\legal_acts`  
- Prefer demo/seed LegalMitra tenants only  
- Do not enable production Claude/`legal_ai` via this runbook  
