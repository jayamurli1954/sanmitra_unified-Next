# LegalMitra Stage 2.1 — Quality Gate + Citation Audit

**Document type:** Architecture / foundation design note  
**Product:** LegalMitra  
**Status:** Stage 2.1 — statute-first Citation Audit + Quality Gate **complete for engineering exit** (2026-08-16); case-law citator and multi-claim rewriting remain deferred  
**Date:** 2026-08-16  
**Workspace:** `D:\sanmitra_unified-Next`

This note turns two external *patterns* into a SanMitra-native Stage 2.1 plan:

| Borrowed idea (pattern only) | Source inspiration (not a dependency) |
| --- | --- |
| Pre-delivery **Quality Gatekeeper** (jurisdiction, citations, completeness) | LexEdge Open Legal Agents — agent role design |
| Post-retrieval **citation / claim audit** with evidence trail | Hallucination Auditor — VERIFIED / ERROR / UNVERIFIABLE outcomes |

No repository above is cloned, vendored, or forked into this workspace. Implementation must stay inside LegalMitra’s existing hybrid research path, response contract, tenant/app isolation, and `legalmitra-compliance` rules.

---

## 1. Related controls

| Artifact | Role |
| --- | --- |
| `docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md` | Product stages and trust gates |
| `docs/architecture/LEGALMITRA_RAG_RESPONSE_CONTRACT.md` | Stage 2 response fields and fallback rules |
| `docs/architecture/LEGALMITRA_ARCHITECTURE_SPEC.md` | Code surfaces and stack |
| `docs/operations/LEGALMITRA_STAGING_RAG_VERIFICATION.md` | Staging RAG enablement |
| `AGENTS.md` + `legalmitra-compliance` skill | Tenant, attribution, human-review, no fabricated authority |

---

## 2. Current state (what Stage 2 / 2.1 already has)

Already shipped in the unified repo (as of Stage 2 + Stage 2.1 trust layers):

- Structured research response via `app/modules/legal_compat/response_contract.py`
  (`jurisdiction`, `answer_summary`, `citations`, `confidence`, `limitations`,
  `human_review_required`, `advisory_notice`, refusal paths).
- Cite-or-refuse hybrid path: no relevant RAG / authorized offline sources →
  `insufficient_sources` (no uncited model memory as grounded research).
- Missing-jurisdiction and fabrication-request refusals.
- Statute verifier for known BNSS / CrPC mapping mistakes on generated text.
- Answer feedback API + GST §54 / IT §139 offline slices + Stage 2 eval harness.
- Relevance filtering of retrieved citations before prompt context.
- **Stage 2.1 (implemented):** `quality_gate.py` + `citation_audit.py` wired through
  `_apply_trust_layers` on hybrid research returns. Statute section claims in the
  answer must appear in citation evidence or the response is refused. Responses
  carry `quality_gate` and (when audited) `citation_audit`.

What is still **not** done:

- Systematic multi-sentence legal-rule claim segmentation beyond section numbers.
- Mismatch → safe rewrite loop (current policy: refuse).
- Indian case-law existence / proposition citators.

---

## 3. Target state (Stage 2.1)

Every hybrid research answer that leaves the server should pass two layers:

```text
Query
  → retrieve / authorized offline
  → (optional) generate from retrieved context only
  → Citation Audit (claim ↔ source)
  → Quality Gate (contract completeness)
  → finalize_research_response / insufficient_sources
```

### 3.1 Quality Gate (pre-delivery)

A deterministic gate runs on the structured payload **after** generation or
authorized offline assembly, **before** the HTTP response is returned.

| Check ID | Rule | Fail action |
| --- | --- | --- |
| `QG-JURISDICTION` | Jurisdiction-dependent question has resolved jurisdiction (or explicit missing-jurisdiction response). | Missing-jurisdiction / refuse |
| `QG-CITATIONS` | If `confidence` ≠ `insufficient_sources`, at least one enriched citation is present. | Downgrade to insufficient_sources |
| `QG-HUMAN-REVIEW` | `human_review_required === true` | Force true + log |
| `QG-ADVISORY` | Advisory notice present | Inject contract notice |
| `QG-NO-FABRICATION` | Response text must not introduce statute/case identifiers absent from citations / authorized offline payload / verifier allow-list. | Strip claim or refuse |
| `QG-COMPLETENESS` | Required contract fields present (`question`, `confidence`, `limitations`, `generated_at`, strategy). | Fill defaults or refuse |
| `QG-AUDIT` | If citation audit ran, no `mismatch` claims remain in the user-visible answer without an explicit limitation. | Add limitation or refuse |

Gate output (internal, also optionally returned under `quality_gate` for admin/debug):

```json
{
  "passed": true,
  "checks": [
    {"id": "QG-CITATIONS", "status": "pass"},
    {"id": "QG-NO-FABRICATION", "status": "pass"}
  ],
  "failed_ids": []
}
```

### 3.2 Citation Audit (post-retrieval / post-generation)

For answers that include generated analysis, split the answer into **atomic claims**
that assert legal rules (section numbers, duties, timelines, rates). For each claim:

| Outcome | Meaning | UI / contract effect |
| --- | --- | --- |
| `verified` | Claim is supported by at least one retrieved/authorized snippet (overlap or structured section match). | Keep claim; citation remains |
| `mismatch` | Claim cites or implies an authority that contradicts retrieved text, or invents a section not in sources. | Remove/rewrite claim or refuse; record limitation |
| `unverifiable` | Claim is too vague or sources lack enough text to confirm. | Keep only if marked low confidence + limitation; else refuse |

Audit is **Indian-corpus first**:

- Primary: tenant/app RAG chunks + Stage 2 authorized offline GST/IT slices.
- Secondary (planned, not Stage 2.1 required): India Code / official gazette /
  court metadata where ingest exists.
- Out of scope: BAILII, Find Case Law, CourtListener as default authorities.

Suggested response extension (additive; keep Stage 2 fields stable):

| Field | Required in 2.1 | Purpose |
| --- | --- | --- |
| `quality_gate` | Yes (internal; optional in client payload) | Pass/fail checklist |
| `citation_audit` | Yes when generation ran | Summary counts + per-claim outcomes |
| `citation_audit.claims[].outcome` | Yes when audited | `verified` \| `mismatch` \| `unverifiable` |
| `citation_audit.claims[].evidence_chunk_ids` | When verified | Links to citations used |

### 3.3 Instrumentation

Extend answer-feedback / ops metrics (no PII in aggregates):

- Gate fail rate by check ID.
- Audit outcome mix (`verified` / `mismatch` / `unverifiable`).
- Correlation with user thumbs-down feedback.

---

## 4. Gap

| Gap | Notes |
| --- | --- |
| Multi-sentence claim segmentation | Statute section audit shipped; broader legal-rule claims deferred |
| Mismatch → rewrite loop | Failures prefer refuse or authorized offline fallthrough |
| Case-law citator for India | Deferred; statute-section audit first (GST/IT) |
| Provider-path audit evidence | External counsel still needs stronger `source_backed` audit fields (existing contract gap) |

---

## 5. Implementation sequence

Keep this **narrow**. Do not expand into LexEdge-style multi-agent product UI.

1. **Extract Quality Gate helper** in `legal_compat` (pure functions over the
   finalized contract dict). Wire at the end of `build_hybrid_legal_response`
   and authorized offline finalize paths.
2. **Add unit tests** for each `QG-*` fail path using existing GST/IT fixtures.
3. **Citation audit v1 (statute-only):** for answers that mention `Section N`
   / act names, require that N appears in citation snippets or offline payload;
   else `mismatch` → refuse or strip.
4. **Attach `citation_audit` summary** to response (and optionally store
   counts with answer feedback).
5. **Eval harness:** extend Stage 2 eval with mismatch fixtures (wrong section
   numbers) that must refuse or correct via gate—not pass as grounded.
6. **UI:** show a compact “Sources checked” line on the research answer card
   when audit ran (verified count / limitations). No fake confidence theater.
7. **Defer:** multi-agent router, contract redline agents, UK citators,
   judgment summarization (MILDSum), BERT pretraining.

### Suggested code homes (target / current)

| Concern | Location |
| --- | --- |
| Quality Gate | `app/modules/legal_compat/quality_gate.py` (**implemented**) |
| Citation Audit | `app/modules/legal_compat/citation_audit.py` (**implemented**) |
| Statute crosswalk | `app/modules/legal_compat/statute_normalize.py` (**implemented**; BNSS 504 preserved outside CrPC-482 context) |
| Criminal code registry | `data/legal_seed/india_criminal_code_crosswalk_v1.json` + `code_crosswalk.py` + `/legalmitra/code-crosswalk` API (**implemented**; curated seed) |
| Wire-up | `app/modules/legal_compat/service.py` (`apply_research_trust_layers`) |
| Tests | `tests/test_legalmitra_stage21_quality_gate.py`, statute verification tests |
| Eval fixtures | `tests/fixtures/legalmitra_citation_mismatch_eval.json` + `scripts/run_legalmitra_stage21_mismatch_eval.py` (**implemented**) |

---

## 6. Success criteria (Stage 2.1 exit)

Stage 2.1 is **done** when:

- Every research response either passes Quality Gate or is an explicit
  insufficient-sources / missing-jurisdiction refusal.
- On the GST/IT eval set, fabricated section numbers in model output are
  caught as `mismatch` ≥ **95%** of injected-fault cases (fault fixtures).
- Existing Stage 2 grounding bar remains ≥ **95%** (no regression).
- `human_review_required` and advisory notice remain mandatory.
- No third-party legal-agent repo is added as a dependency or submodule.
- Staging RAG verification runbook still passes when RAG is enabled.

**Engineering exit:** Accepted 2026-08-16 — see
`docs/operations/LEGALMITRA_STAGE2_EXIT_SIGNOFF.md`.

---

## 7. Non-goals / deferred

- Cloning LexEdge, Legal Co-Pilot, LegalOS, or Hallucination Auditor codebases.
- Google ADK multi-agent console or WebSocket agent product shell.
- Automatic e-filing, e-sign, or outbound negotiation email.
- Full case-law existence checks for Indian courts (needs separate corpus/API).
- Replacing hybrid research with an unsupervised agent swarm.
- Spreading this gate to MandirMitra / GruhaMitra / MitraBooks AI surfaces.

---

## 8. Risk notes

| Risk | Mitigation |
| --- | --- |
| Over-refusal reduces usefulness | Gate only legal-rule claims; keep procedural UI copy ungated |
| Naive string match false positives | Prefer section-number + act-name co-occurrence against citation text |
| Silent rewrite changes legal meaning | Prefer refuse + limitation over auto-rewrite of statutory content |
| Confidential text in audit logs | Store outcome counts and chunk IDs; not full prompts by default |

---

## 9. Decision

**Accepted direction:** implement Stage 2.1 as SanMitra-native Quality Gate +
statute-first Citation Audit on top of the existing Stage 2 response contract.

**Not accepted:** product forks or dependency on the reviewed external legal-AI
repositories.
