# CGST Section 54 — curated judgment digests (starter)

**Current:** Offline retrieve-or-refuse for “referred cases” / judgment queries on the Stage 2 GST §54 package. Digests live under this folder and are loaded by `app/modules/legal_compat/judgment_retrieval.py`.

**Target:** Broader judgment corpus (limitation-specific holdings, HC digests) plus optional tenant RAG ingest of full texts.

**Gap:** Only a starter digest set is shipped. Missing matches still refuse — LegalMitra will not invent case names.

## Contents

| File | Case | Focus |
| --- | --- | --- |
| `union_of_india_v_vkc_footsteps_2021.json` | Union of India v. VKC Footsteps India Pvt. Ltd. (2021 INSC 469) | s.54(3) inverted-duty refund / Rule 89(5) — **not** s.54(1) limitation |

## Rules

- Curated digests only; verify against the original reported decision.
- Retrieval must attribute court, citation, date, and topic focus.
- If no digest matches, keep the refuse text (no invented authorities).
