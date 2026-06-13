# External Integration Plan

## Purpose

This document captures external integrations discussed for LegalMitra in the unified platform. InvestMitra integrations are intentionally out of SanMitra unified backend and deployment scope.

Current state: LegalMitra now has a provider-gated Claude Legal Counsel call path in the legal research pipeline. InvestMitra may be developed separately for personal use only.

## Summary

| Integration | Product | Purpose | Execution Boundary |
| --- | --- | --- | --- |
| Claude for Legal | LegalMitra | Legal workflow assistant, drafting/review/research support | Human review, source attribution, confidentiality |

## Phase 0: Documentation and Risk Review

Before coding:

- Confirm licensing and commercial-use constraints.
- Confirm data retention and privacy rules.
- Confirm whether integrations are tenant-level, user-level, or both.
- Define allowed and forbidden tool methods.
- Define audit logging requirements.
- Define UI disclaimers and human-review workflow.

## Phase 1: Adapter Interfaces

Create internal adapter boundaries without provider-specific UI assumptions.

Suggested shape:

```text
app/integrations/
  legal_ai/
    base.py
    claude_for_legal.py
```

No external tool should be called directly from frontend code.

## Phase 2: Read-Only Proofs of Concept

### Claude Legal Counsel POC

- Current implementation path: LegalMitra calls Claude Legal Counsel first when `CLAUDE_LEGAL_COUNSEL_ENABLED=true` and `ANTHROPIC_API_KEY` is configured.
- Fallback path: if Claude is not configured or fails, LegalMitra falls back to Gemini and then narrow offline safeguards where available.
- Current statutory verification guardrail: LegalMitra injects and enforces a canonical high-risk criminal-law crosswalk for the CrPC 482 inherent-powers route. Generated references to BNSS Section 504 or 538 for CrPC 482 are normalized to BNSS Section 528 with a caution note before the response leaves `/api/v1/legal-research`.
- Preserve source citations.
- Require human review before output is finalized.
- Validate tenant isolation and confidentiality.

## Phase 3: Product Integration

### LegalMitra

Add legal assistant screens:

- Document review.
- Drafting support.
- Case summarization.
- Compliance checklist assistance.
- Citation verification workflow.

Current gap:

- Claude Legal Counsel is wired as a backend provider path for `/api/v1/legal-research`.
- Production readiness still requires tenant policy, API key configuration, confidentiality review, and live E2E pass/fail notes.

## Phase 4: Tenant/Plan Enablement

Enable integrations only via module flags:

- `legal_ai`

Default should be off at the module registry level until each integration passes security, licensing, and workflow review. The LegalMitra backend provider path can still be tested locally with explicit API key configuration before module-wide enablement.

## Non-Negotiable Guardrails

### LegalMitra

- No uncited legal research answer.
- No hallucinated citations.
- No final legal advice without lawyer/user review.
- Preserve client confidentiality.
- Log access according to tenant policy.
