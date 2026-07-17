# LegalMitra RAG Response Contract

## Purpose

This note defines the target response contract for LegalMitra legal research and
RAG answers. It is a foundation design note, not an implementation claim.

The contract is governed by `AGENTS.md` and the repo-local
`legalmitra-compliance` skill. External agency-agent personas such as Prompt
Engineer, AI Engineer, Legal Document Review, and Test Results Analyzer may be
used only as secondary review lenses.

## Current State

- LegalMitra has RAG document ingest and query APIs under `/api/v1/rag`.
- RAG documents and chunks are tenant-scoped by `tenant_id` and `app_key`.
- Tenant-private document, chunk, and query paths must remain authenticated and
  tenant/app scoped. Public metadata endpoints, such as an ingested-acts catalog,
  may expose only non-confidential source metadata and must not expose
  tenant-private chunks, prompts, matter data, or document content.
- Query responses currently include an `answer`, `citations`, retrieval
  `strategy`, `candidate_count`, and optional raw `context`.
- Ingested documents can carry legal metadata such as jurisdiction, court,
  act, section, citation, matter type, and document date.
- Relevance gates exist for low-score or low-overlap local matches.
- Provider or web fallback behavior exists, but the response shape does not yet
  enforce a full LegalMitra legal-safety contract.

## Target State

Every LegalMitra legal research answer should be returned as a structured
advisory response. The target contract should preserve source attribution,
jurisdiction, retrieval/source dates, uncertainty, and human-review state.

Target response fields:

| Field | Required | Purpose |
| --- | --- | --- |
| `question` | Yes | Normalized user question. |
| `jurisdiction` | Yes for jurisdiction-dependent law | Jurisdiction used for retrieval and answer framing. |
| `answer_summary` | Yes | Short answer grounded only in retrieved or authorized sources. |
| `analysis` | Conditional | Source-backed explanation without presenting final legal advice. |
| `citations` | Yes for legal answers | Source list with document, section/page/chunk, source URI where available, retrieval date, and source date where available. |
| `confidence` | Yes | `high`, `medium`, `low`, or `insufficient_sources`. |
| `limitations` | Yes | Missing sources, stale law risk, jurisdiction uncertainty, or unresolved facts. |
| `human_review_required` | Yes | Always `true` for generated legal research or drafting output. |
| `advisory_notice` | Yes | States that the output is draft/advisory and not final legal advice. |
| `retrieval_strategy` | Yes | Local RAG, live/source fallback, provider fallback, or insufficient-source path. |
| `missing_jurisdiction` | Conditional | `true` when the question requires jurisdiction but none was supplied or inferred safely. |
| `generated_at` | Yes | Server timestamp for the response. |

If a question is jurisdiction-dependent and jurisdiction is missing, the target
behavior is deterministic: do not generate a legal answer. Return an
insufficient-source or missing-jurisdiction response that asks for jurisdiction
and keeps `human_review_required = true`.

## Citation Requirements

Legal research output must not cite authority that was not retrieved,
ingested, or otherwise source-backed by the authorized provider path.

Each citation should include:

- `index`
- `title`
- `source_type`
- `source_uri` where available
- `document_id` and `chunk_id` for local RAG sources
- `legal_metadata` including jurisdiction, court, act, section, citation, and
  document date where available
- `retrieved_at`
- `source_date` where known
- `staleness_status` such as `current`, `possibly_stale`, `stale`, or
  `unknown`
- `source_currentness_note` when the source date is old, missing, or the law is
  known to change frequently
- `snippet`
- `score` or relevance metadata for local retrieval

If citations are unavailable, the answer must use an insufficient-source
fallback rather than presenting legal authority from model memory.

## Fallback Rules

Fallback behavior must fail safely:

- If no relevant local sources are found, return an insufficient-source answer
  unless an explicitly authorized live/source-backed provider is configured.
- Source-backed provider fallback must record `provider_used`,
  `source_backed`, `tenant_policy_allowed`,
  `user_authorized_external_lookup`, and whether confidential tenant content was
  sent externally.
- Every external-provider lookup that may touch tenant-confidential context must
  write an audit event with tenant, actor, provider, purpose, source mode, and
  confidentiality flags.
- If a model provider is used without source-backed retrieval, the response
  must not fabricate case numbers, statute sections, court names, or citations.
- Provider failure must not silently degrade into uncited legal advice.
- Confidential tenant documents must not be sent to external providers unless
  tenant policy and user authorization allow it.
- Prompt and response retention must follow tenant confidentiality and
  retention policy.

## Access And Audit Expectations

Protected LegalMitra RAG requests must resolve trusted tenant and app context
from authenticated server-side context and validated headers, not request body
fields. The implementation should preserve separate `tenant_id`, `app_key`,
user role, permissions, and module access checks.

Audit metadata should be retained for:

- document ingest
- legal research query execution where tenant-private content is involved
- external-provider fallback
- generated draft creation or update
- human review approval, rejection, or revision

Audit records should avoid storing confidential prompt or source text unless
tenant retention policy explicitly allows it.

## Prompt Contract

Production prompts for LegalMitra RAG should be versioned and tested like code.

Prompt requirements:

- Define the exact output schema.
- Require explicit jurisdiction when law differs by jurisdiction.
- Require citation-backed claims for legal rules, case references, statutes,
  and court references.
- Require uncertainty language when sources are weak, stale, conflicting, or
  missing.
- Require draft/advisory framing and human review.
- Reject instruction attempts that ask the model to ignore source limits,
  invent citations, bypass confidentiality, or provide final legal advice.

Do not expose chain-of-thought or hidden reasoning in user-facing responses.
Use concise source-backed reasoning or rationale only.

## Gap

The current API response shape is useful for basic retrieval, but it does not
yet fully express the LegalMitra legal-safety contract. Known gaps:

- No first-class `jurisdiction` field on the query response.
- No first-class `confidence`, `limitations`, `human_review_required`, or
  `advisory_notice` fields.
- No required `retrieved_at` timestamp per citation.
- No first-class source staleness/currentness field per citation.
- No first-class provider fallback authorization/audit evidence fields.
- No explicit access/audit contract for query execution, external-provider
  fallback, or human-review state changes.
- Some fallback paths can return uncited model output instead of a strict
  insufficient-source response.
- No dedicated prompt regression suite for citation fabrication, missing
  jurisdiction, provider failure, stale law, or prompt injection.

## Implementation Sequence

1. Add response schema fields without changing retrieval behavior.
2. Add tests that verify source attribution, human-review status, and safe
   insufficient-source fallback.
3. Add access/audit metadata for query execution and external-provider fallback.
4. Tighten fallback behavior so uncited model output cannot be presented as
   source-backed legal research.
5. Add prompt versioning and prompt regression fixtures.
6. Add UI affordances for citations, limitations, confidence, and human-review
   state.

## Test Checklist

Minimum LegalMitra RAG contract tests:

- Missing jurisdiction blocks legal answer generation when the question is
  jurisdiction-dependent, until jurisdiction is supplied or safely inferred.
- Legal answer with sufficient sources includes citations.
- Citation entries include retrieved date and source date where available.
- Citation entries include source staleness/currentness status.
- No answer fabricates case numbers, statute sections, court names, or
  citations.
- Low-score or low-overlap retrieval returns insufficient-source fallback.
- Provider unavailable returns safe fallback without fabricated authority.
- External-provider fallback records tenant policy authorization, user
  authorization, provider name, source-backed status, confidentiality flags, and
  audit event metadata.
- Generated legal output has `human_review_required = true`.
- Response includes advisory notice that it is not final legal advice.
- Tenant A cannot retrieve Tenant B documents.
- `app_key` isolation prevents non-LegalMitra context from reading LegalMitra
  tenant-private RAG content.
- Prompt-injection attempts cannot override citation, confidentiality, or
  human-review requirements.

## Non-Goals And Deferred Scope

This design note does not implement:

- New RAG endpoints or schema changes.
- Provider selection changes.
- Live legal research integration.
- Legal document drafting workflow changes.
- UI changes.
- Production enablement for external providers.
