# LegalMitra Stage 2 / 2.1 — Engineering Exit Sign-off

**Product:** LegalMitra  
**Date:** 2026-08-16  
**Status:** Engineering exit **accepted** for Stage 2 research trust + Stage 2.1 statute-first Quality Gate / Citation Audit  
**Workspace:** `D:\sanmitra_unified-Next`

This is an **engineering** sign-off. The PRD commercial adoption gate (paying users / sustained usage) remains a parallel go-to-market criterion for expanding Stage 3 depth — it does not block declaring the Stage 2 research trust bar met in code.

---

## 1. Stage 2 exit (research trust)

| Criterion | Evidence |
| --- | --- |
| GST/IT eval grounding ≥ 95% | `python scripts/run_legalmitra_stage2_eval.py --min-grounding 0.95` |
| Cite-or-refuse + advisory + human review | Response contract + hybrid path tests |
| Authorized offline slices | CGST §54 senior-counsel package; IT §139 slice |
| Feedback instrumentation | `/api/v1/legalmitra/answer-feedback` + summary |
| Live / staging corpus ops | `docs/operations/LEGALMITRA_STAGING_RAG_VERIFICATION.md` (operator runbook) |

## 2. Stage 2.1 exit (Quality Gate + Citation Audit)

| Criterion | Evidence |
| --- | --- |
| Every research response passes Quality Gate or is an explicit refusal | `quality_gate.py` + hybrid wiring |
| Fabricated section numbers caught ≥ 95% on fault fixtures | `python scripts/run_legalmitra_stage21_mismatch_eval.py --min-catch-rate 0.95` |
| Stage 2 grounding bar not regressed | Stage 2 eval above |
| UI shows Sources checked when audit ran | `frontend/legalmitra/answer-trust.js` |
| No third-party legal-agent dependency | Policy unchanged |

## 3. Explicitly deferred (not Stage 2/2.1 blockers)

- Indian case-law existence / proposition citators  
- Automatic judgment retrieval for “referred cases” queries (corpus ingest + retrieval depth)
  — **partial:** starter CGST §54 curated digests (VKC Footsteps) retrieve-or-refuse in the
  offline package when cases are requested; broad corpus / citators still deferred  
- Multi-sentence claim segmentation beyond statute section numbers  
- Mismatch → safe rewrite loop (current policy: refuse or authorized offline fallthrough)  
- Full Bare Act / judgment corpus expansion beyond GST/IT Stage 2 depth  
- Commercial adoption gate for Stage 3 expansion  

## 4. Next focus

Move primary engineering attention to **Stage 3 — Matter / Client Intelligence** completion and hardening, while keeping Stage 2 regression green.

## 5. Commands (local)

```powershell
D:\sanmitra_unified-Next\.venv\Scripts\python.exe scripts/run_legalmitra_stage2_eval.py --min-grounding 0.95
D:\sanmitra_unified-Next\.venv\Scripts\python.exe scripts/run_legalmitra_stage21_mismatch_eval.py --min-catch-rate 0.95
D:\sanmitra_unified-Next\.venv\Scripts\python.exe -m pytest tests/test_legalmitra_stage21_quality_gate.py tests/test_legalmitra_rag_contract.py -q
```
