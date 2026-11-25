"""Stage 2.1 Quality Gate for LegalMitra research responses.

Deterministic pre-delivery checks on the Stage 2 response contract.
Borrowing gatekeeper *ideas* only — no third-party agent framework.
"""
from __future__ import annotations

from typing import Any

from app.modules.legal_compat.response_contract import ADVISORY_NOTICE


def _check(
    check_id: str,
    *,
    passed: bool,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "pass" if passed else "fail",
        "detail": detail,
    }


def run_quality_gate(
    payload: dict[str, Any],
    *,
    citation_audit: dict[str, Any] | None = None,
    skip_citation_presence: bool = False,
) -> dict[str, Any]:
    """Evaluate gate checks; does not mutate payload."""
    strategy = str(payload.get("strategy") or "")
    confidence = str(payload.get("confidence") or "")
    citations = list(payload.get("citations") or [])
    is_refusal = strategy in {"insufficient_sources", "missing_jurisdiction"}
    checks: list[dict[str, Any]] = []

    # QG-JURISDICTION
    if payload.get("missing_jurisdiction"):
        checks.append(_check("QG-JURISDICTION", passed=True, detail="missing_jurisdiction response"))
    elif is_refusal:
        checks.append(_check("QG-JURISDICTION", passed=True, detail="refusal path"))
    else:
        checks.append(
            _check(
                "QG-JURISDICTION",
                passed=bool(payload.get("jurisdiction")),
                detail="jurisdiction required for non-refusal answers",
            )
        )

    # QG-CITATIONS
    if skip_citation_presence or is_refusal or confidence == "insufficient_sources":
        checks.append(_check("QG-CITATIONS", passed=True, detail="refusal or skip"))
    else:
        checks.append(
            _check(
                "QG-CITATIONS",
                passed=len(citations) > 0,
                detail="at least one citation required when not refusing",
            )
        )

    # QG-HUMAN-REVIEW
    checks.append(
        _check(
            "QG-HUMAN-REVIEW",
            passed=payload.get("human_review_required") is True,
            detail="human_review_required must be true",
        )
    )

    # QG-ADVISORY
    advisory = str(payload.get("advisory_notice") or "").strip()
    checks.append(
        _check(
            "QG-ADVISORY",
            passed=bool(advisory),
            detail="advisory_notice required",
        )
    )

    # QG-COMPLETENESS
    required_ok = all(
        [
            str(payload.get("question") or "").strip(),
            str(payload.get("confidence") or "").strip(),
            isinstance(payload.get("limitations"), list),
            str(payload.get("generated_at") or "").strip(),
            str(payload.get("strategy") or payload.get("retrieval_strategy") or "").strip(),
        ]
    )
    checks.append(_check("QG-COMPLETENESS", passed=required_ok, detail="core contract fields"))

    # QG-AUDIT — mismatch must not remain on a non-refusal answer
    if citation_audit is None or is_refusal:
        checks.append(_check("QG-AUDIT", passed=True, detail="no live audit or already refused"))
    else:
        mismatch = int(citation_audit.get("mismatch_count") or 0)
        checks.append(
            _check(
                "QG-AUDIT",
                passed=mismatch == 0,
                detail=f"mismatch_count={mismatch}",
            )
        )

    # QG-NO-FABRICATION mirrors audit for section mismatches (statute-first v1)
    if citation_audit is None or is_refusal:
        checks.append(_check("QG-NO-FABRICATION", passed=True, detail="skipped"))
    else:
        mismatch = int(citation_audit.get("mismatch_count") or 0)
        checks.append(
            _check(
                "QG-NO-FABRICATION",
                passed=mismatch == 0,
                detail="statute section claims must appear in citation evidence",
            )
        )

    # QG-CASE-CITATIONS — no case authority outside retrieved evidence may remain
    case_audit = payload.get("case_citation_audit")
    if not isinstance(case_audit, dict) or is_refusal:
        checks.append(_check("QG-CASE-CITATIONS", passed=True, detail="no case audit or refusal"))
    else:
        remaining = int(case_audit.get("remaining_unsupported_count") or 0)
        checks.append(
            _check(
                "QG-CASE-CITATIONS",
                passed=remaining == 0,
                detail=(
                    f"unsupported={int(case_audit.get('unsupported_count') or 0)} "
                    f"redacted={int(case_audit.get('redacted_count') or 0)} remaining={remaining}"
                ),
            )
        )

    failed_ids = [c["id"] for c in checks if c["status"] == "fail"]
    return {
        "passed": not failed_ids,
        "checks": checks,
        "failed_ids": failed_ids,
    }


def enforce_quality_gate(
    payload: dict[str, Any],
    *,
    citation_audit: dict[str, Any] | None = None,
    skip_citation_presence: bool = False,
) -> dict[str, Any]:
    """Attach quality_gate; repair soft contract fields; leave hard fails flagged.

    Hard citation/fabrication failures are expected to be converted to
    insufficient_sources by the hybrid caller before this runs, or detected here
    via failed_ids for callers that prefer explicit handling.
    """
    out = dict(payload)
    if out.get("human_review_required") is not True:
        out["human_review_required"] = True
    if not str(out.get("advisory_notice") or "").strip():
        out["advisory_notice"] = ADVISORY_NOTICE
    if citation_audit is not None:
        out["citation_audit"] = citation_audit

    # Soft: unverifiable-only claims → extra limitation + low confidence nudge
    if citation_audit and int(citation_audit.get("unverifiable_count") or 0) > 0:
        limitations = list(out.get("limitations") or [])
        note = (
            "One or more statute section claims could not be verified against "
            "retrieved citation text."
        )
        if note not in limitations:
            limitations.append(note)
        out["limitations"] = limitations
        if out.get("confidence") == "high":
            out["confidence"] = "medium"

    gate = run_quality_gate(
        out,
        citation_audit=citation_audit,
        skip_citation_presence=skip_citation_presence,
    )
    out["quality_gate"] = gate
    return out


# Human-curated, authorized offline packages: their case authorities are vetted
# content, not model memory, so the case-citation gate does not redact them.
_CURATED_STRATEGY_PREFIXES = ("offline_", "deterministic_")

CASE_REDACTION_LIMITATION = (
    "Case citations not found in the retrieved sources were removed. LegalMitra "
    "only cites cases it can trace to a retrieved or authorized source."
)


def apply_case_citation_gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Redact case names / law-report citations not traceable to citations.

    Returns a new payload with ``case_citation_audit`` attached. Statutory
    analysis is kept; only the unsupported authorities are removed.
    """
    from app.modules.legal_compat.case_citation_audit import (
        audit_case_citations,
        redact_unsupported_case_citations,
    )

    out = dict(payload)
    strategy = str(out.get("strategy") or "")
    if strategy.startswith(_CURATED_STRATEGY_PREFIXES):
        return out

    citations = list(out.get("citations") or [])
    redacted, audit = redact_unsupported_case_citations(
        response_text=str(out.get("response") or ""),
        citations=citations,
    )
    recheck = audit_case_citations(response_text=redacted, citations=citations)
    audit["remaining_unsupported_count"] = int(recheck.get("unsupported_count") or 0)
    # Keep the report compact: span offsets are only meaningful pre-redaction.
    audit["claims"] = [
        {"claim_type": c["claim_type"], "text": c["text"], "outcome": c["outcome"]}
        for c in audit.get("claims") or []
    ]
    out["case_citation_audit"] = audit

    if int(audit.get("unsupported_count") or 0) > 0:
        out["response"] = redacted
        if out.get("answer_summary"):
            summary, _ = redact_unsupported_case_citations(
                response_text=str(out["answer_summary"]), citations=citations
            )
            out["answer_summary"] = summary
        limitations = list(out.get("limitations") or [])
        if CASE_REDACTION_LIMITATION not in limitations:
            limitations.append(CASE_REDACTION_LIMITATION)
        out["limitations"] = limitations
        if out.get("confidence") == "high":
            out["confidence"] = "medium"
    return out


_SKIP_AUDIT_STRATEGIES = frozenset(
    {
        "insufficient_sources",
        "missing_jurisdiction",
        "deterministic_indian_acts_list",
    }
)


def apply_research_trust_layers(payload: dict[str, Any]) -> dict[str, Any]:
    """Run case-citation gate, statute citation audit + quality gate on a research payload."""
    from app.modules.legal_compat.citation_audit import audit_statute_section_claims
    from app.modules.legal_compat.response_contract import insufficient_sources_response

    strategy = str(payload.get("strategy") or "")
    if strategy in _SKIP_AUDIT_STRATEGIES:
        return enforce_quality_gate(payload, citation_audit=None, skip_citation_presence=True)

    payload = apply_case_citation_gate(payload)
    audit = audit_statute_section_claims(
        response_text=str(payload.get("response") or ""),
        citations=list(payload.get("citations") or []),
    )
    if int(audit.get("mismatch_count") or 0) > 0:
        refused = insufficient_sources_response(
            question=str(payload.get("question") or ""),
            jurisdiction=payload.get("jurisdiction"),
            dropped_citation_count=int(payload.get("dropped_citation_count") or 0),
            note=(
                "Stage 2.1 citation audit found statute section claims "
                "not supported by retrieved or authorized sources."
            ),
        )
        return enforce_quality_gate(refused, citation_audit=audit, skip_citation_presence=True)

    return enforce_quality_gate(payload, citation_audit=audit)


def accept_or_record_audit_refusal(
    payload: dict[str, Any],
    *,
    last_refused: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return trusted payload, or None when Stage 2.1 audit refuses generation.

    Callers can then try the next provider / RAG extractive answer instead of
    short-circuiting on insufficient_sources (important when LEGAL_RAG_ENABLED=true).
    """
    trusted = apply_research_trust_layers(payload)
    if str(trusted.get("strategy") or "") != "insufficient_sources":
        return trusted
    last_refused.clear()
    last_refused.append(trusted)
    return None
