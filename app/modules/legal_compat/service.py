from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import BackgroundTasks

from app.config import get_settings
from app.modules.legal_compat.offline_fallbacks import offline_legal_fallback as _offline_legal_fallback
from app.modules.legal_compat.quality_gate import (
    accept_or_record_audit_refusal,
    apply_research_trust_layers,
)
from app.modules.legal_compat.response_contract import (
    finalize_research_response,
    insufficient_sources_response,
    missing_jurisdiction_response,
    resolve_jurisdiction,
)
from app.modules.legal_compat.statute_normalize import (
    CANONICAL_STATUTE_CROSSWALK as _CANONICAL_STATUTE_CROSSWALK,
    normalize_verified_statute_mappings,
)
from app.modules.legal_compat.sync_queue import enqueue_auto_sync_query

_logger = logging.getLogger(__name__)

_FABRICATION_REQUEST_RE = re.compile(
    r"\b(invent|fabricate|make up|hallucinate|fake citation|secretly|unpublished)\b",
    re.IGNORECASE,
)

_CLOSING_DISCLAIMER = (
    "\n\n---\n"
    "*Disclaimer: This note is prepared for the use of the instructing advocate only. "
    "Verify the current legal position, recent amendments, and jurisdiction-specific practice "
    "before filing, advising a client, or taking final legal action. "
    "No professional liability attaches to this output.*"
)

_IST_TZ = timezone(timedelta(hours=5, minutes=30))

# ─── Utilities ────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_ist() -> datetime:
    return datetime.now(_IST_TZ)


def _normalize_query(query: str) -> str:
    return " ".join((query or "").strip().lower().split())


def extract_current_legal_query(query: str) -> str:
    """Return the latest user question when callers accidentally include chat history."""
    value = (query or "").strip()
    if not value:
        return ""

    quoted_questions = re.findall(r'["\u201c\u201d]([^"\u201c\u201d\n\r]{8,500}\?)["\u201c\u201d]?', value)
    if quoted_questions:
        return " ".join(quoted_questions[-1].split())

    # Avoid unbounded regex over chat-history-sized input. CodeQL flags lazy
    # dot-star patterns on uncontrolled text, so use bounded marker scanning.
    marker_scan = value[:4000]
    marker_scan_lower = marker_scan.lower()
    for marker in (
        "current question",
        "current query",
        "latest question",
        "latest query",
        "user question",
        "user query",
        "user's question",
        "user's query",
    ):
        marker_at = marker_scan_lower.rfind(marker)
        if marker_at < 0:
            continue

        tail = marker_scan[marker_at + len(marker) :]
        tail_stripped = tail.lstrip()
        if tail_stripped.startswith(":"):
            candidate = tail_stripped[1:]
        elif tail_stripped.lower().startswith("is"):
            candidate = tail_stripped[2:]
        else:
            continue

        question_end = candidate.find("?")
        if question_end >= 0:
            return " ".join(candidate[: question_end + 1].split())

    question_lines = [
        line.strip()
        for line in value.splitlines()
        if "?" in line and not re.search(r"\b(previous|prior|earlier)\s+(turn|query|question)\b", line, re.IGNORECASE)
    ]
    if question_lines:
        return " ".join(question_lines[-1].split())

    return " ".join(value.split())


def _rag_answer_insufficient(answer: str) -> bool:
    value = (answer or "").strip().lower()
    markers = [
        "do not have enough indexed content",
        "ingest relevant documents",
    ]
    return any(marker in value for marker in markers)


# ─── Format Detection ─────────────────────────────────────────────────────────

_CRIMINAL_MARKERS = re.compile(
    r"\b(ipc|crpc|bns|bnss|bsa|fir|cognizable|bailable|chargesheet|"
    r"section\s+\d|accused|bail|custody|remand|acquittal|conviction|"
    r"evidence act|criminal|penal|offence|offense)\b",
    re.IGNORECASE,
)
_DRAFTING_MARKERS = re.compile(
    r"\b(draft|nda|agreement|deed|clause|contract|mou|memorandum of understanding|"
    r"arbitration clause|non.?disclosure|template|format)\b",
    re.IGNORECASE,
)
_SECTION_LOOKUP_MARKERS = re.compile(
    r"\b(what is|define|meaning of|explain|section \d|article \d|"
    r"under section|under article|interpret|scope of)\b",
    re.IGNORECASE,
)
_CASE_PREP_MARKERS = re.compile(
    r"\b(case prep|argument|submissions|how to argue|strategy|"
    r"hearing|bench questions|oral argument|written submission)\b",
    re.IGNORECASE,
)
_FAMILY_LAW_MARKERS = re.compile(
    r"\b(hindu marriage act|hma|divorce|marriage|matrimonial|family court|"
    r"custody|maintenance|restitution of conjugal rights)\b",
    re.IGNORECASE,
)
_PROCEDURE_GUIDE_MARKERS = re.compile(
    r"\b(procedure|process|steps?|step-by-step|filing|file\s+(a|an)?|"
    r"complaint|petition|application|jurisdiction|limitation|deadline|"
    r"checklist|documents?|format|how\s+to|where\s+to\s+file|"
    r"notice|reply|compliance|tracker|case\s+diary|client\s+work)\b",
    re.IGNORECASE,
)
_NI_ACT_MARKERS = re.compile(
    r"\b(section\s+138|cheque|check|dishonou?r|bounce|ni act|negotiable instruments|"
    r"142\(2\)|142a|demand notice|payee bank|drawee bank)\b",
    re.IGNORECASE,
)


def _detect_format_mode(query: str, query_type: str) -> str:
    """Return one of: cheat_sheet | drafting | quick_check | argument_note"""
    q = extract_current_legal_query(query)
    qt = (query_type or "research").strip().lower()

    if qt == "explain":
        return "legal_advisor"
    if qt in {"advocate_research", "research"}:
        if _PROCEDURE_GUIDE_MARKERS.search(q) or _NI_ACT_MARKERS.search(q):
            return "procedure_guide"
        return "cheat_sheet" if _CRIMINAL_MARKERS.search(q) else "legal_advisor"
    if qt in {"court_strategy", "strategy"}:
        return "court_strategy"
    if qt == "compliance":
        return "compliance"
    if qt == "drafting" or _DRAFTING_MARKERS.search(q):
        return "drafting"
    if qt == "case_prep" or _CASE_PREP_MARKERS.search(q):
        return "argument_note"
    if qt in {"procedure", "procedure_guide", "workflow"} or _PROCEDURE_GUIDE_MARKERS.search(q):
        return "procedure_guide"
    if _FAMILY_LAW_MARKERS.search(q):
        return "legal_advisor"
    if _NI_ACT_MARKERS.search(q):
        return "procedure_guide"
    if _CRIMINAL_MARKERS.search(q):
        return "cheat_sheet"
    if qt in {"section_lookup", "interpretation"} or _SECTION_LOOKUP_MARKERS.search(q):
        return "quick_check"
    # Default to a neutral advisory brief for general research queries.
    return "legal_advisor"


# ─── Prompt Builder ───────────────────────────────────────────────────────────

_SENIOR_COUNSEL_PERSONA = """\
You are LegalMitra — an elite Indian legal advisor and Senior Counsel's Strategic Clerk.
Your mission is to provide accurate, actionable legal guidance for Indian legal users, advocates, professionals, businesses, and individuals.

⚖️ CRITICAL LEGAL GUARDRAILS (NEVER VIOLATE)
1. BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023) ONLY replaces the CrPC (1973). It does NOT replace or amend the IT Act, 2000.
2. For Intermediary Liability & Data Protection:
   - ALWAYS cite Section 79 of the Information Technology Act, 2000 for safe harbor.
   - ALWAYS cite Section 43A of IT Act / SPDI Rules 2011 for legacy data protection.
   - ALWAYS cite the Digital Personal Data Protection (DPDP) Act, 2023 for current data compliance.
   - NEVER map IT Act sections to BNSS sections.
3. The Three New Criminal Laws:
   - BNS 2023 → replaces IPC 1860
   - BNSS 2023 → replaces CrPC 1973
   - BSA 2023 → replaces Indian Evidence Act 1872
   - The IT Act 2000 remains UNCHANGED and independent.

🎯 TONE & STYLE
• Use clear, user-context-aware language. Do not assume the user is a startup founder, SaaS operator, company, freelancer, or advocate unless the query says so.
• When the user's role or purpose is unclear, explain the legal position generally and add practical next steps for a person or organisation as applicable.
• Be Sharp. Authoritative. Action-Oriented.
• Avoid excessive legal theory. Focus on "What to do next".
• Use professional court terminology (e.g. "ratio decidendi", "per incuriam") ONLY when query_type is 'research' or 'case_prep'.
• Prohibited: Behaving like a law student or junior.

JURISPRUDENCE ENGINE
• Prioritise case law over statute text. Cite binding SC precedents first.
• Identify ratio decidendi and classify: ✅ Settled Law | ⚖️ Divergent Views | 🆕 Res Integra

RAG CONTEXT PROTOCOL
• Use [R1], [R2] citations. Prefer retrieved context over model memory.
• If retrieved content conflicts with recalled law, flag the discrepancy clearly.\

CURRENT QUERY DISCIPLINE
• Answer only the CURRENT QUERY section below.
• Do not mention, summarize, or compare any previous turn unless the current query explicitly asks for it.
• If prior chat history appears in the query text, ignore it and answer the latest user question only.\
"""

_FORMAT_DIRECTIVES: dict[str, str] = {
    "cheat_sheet": """\
OUTPUT FORMAT — Cheat Sheet (mandatory for this query)

| Legacy (IPC/CrPC/Evidence Act) | Current (BNS/BNSS/BSA) | Delta | Key SC Case |
|---|---|---|---|
[populate all rows]

Then add a brief Argument Note (3–5 numbered submissions, case-backed).
End with: **Legal Position:** ✅/⚖️/🆕
""",

    "argument_note": """\
OUTPUT FORMAT — STRICT ARGUMENT NOTE

⚠ PROHIBITED: Do NOT write any memo header (MEMORANDUM / To: / From: / Subject: / Date:).
⚠ PROHIBITED: Do NOT write any introduction, preamble, or context-setting paragraph.
⚠ START the response immediately with the bold heading "**Submissions:**" — nothing before it.

**Submissions:**
1. [One precise legal proposition — cite the exact statute section + binding SC case with year and ratio in the same line]
2. [Next proposition — same authority format]
… (as many submissions as the legal position requires; every line must carry authority)

**Legal Position:** ✅ Settled Law / ⚖️ Divergent Views / 🆕 Res Integra
**Risk Exposure:** [concise — limitation period, evidentiary gaps, enforcement difficulty]
**Suggested Action:** Instruct AoR to… / Settle draft prepared by junior…

Authority must accompany every proposition. No narration. No hedging.
""",

    "quick_check": """\
OUTPUT FORMAT — STRICT QUICK CHECK

⚠ PROHIBITED: Do NOT write any memo header (MEMORANDUM / To: / From: / Subject: / Date:).
⚠ PROHIBITED: No introduction. Start the response immediately with "**Provision / Concept:**".

**Provision / Concept:** [exact section + Act + year]
**Core Rule:** [one sentence — what it mandates or permits]
**Ingredients / Tests:** [bullet list]
**Key Exception:** [if any]
**Limitation / Timeline:** [if applicable]
**Key SC Case:** [case name, year, SCC citation — ratio in one line]
**Legal Position:** ✅/⚖️/🆕

Precision only. No narration. No hedging.
""",

    "drafting": """\
OUTPUT FORMAT — FULL DRAFT INSTRUMENT

⚠ PROHIBITED: Do NOT write any memo header (MEMORANDUM / To: / From: / Subject:).
⚠ PROHIBITED: No preamble, no "here is a draft", no advisory wrapper.
⚠ START immediately with the document title (e.g. "NON-DISCLOSURE AGREEMENT").

• Use proper legal numbering (1., 1.1, 1.2…).
• Include all standard clauses: parties, definitions, operative provisions, term, \
termination, governing law, jurisdiction, dispute resolution.
• For NDA/confidentiality: confidentiality obligations, IP assignment, \
return of information, non-solicitation.
• Mark blanks as [PARTY NAME], [DATE], [CITY], etc.
• End with a signature block.
• The advocate will review — do not pre-disclaim or hedge within the document body.
""",

    "legal_advisor": """\
OUTPUT FORMAT — PRACTICAL LEGAL ADVISOR

⚠ START the response immediately with a "🧾 **Quick Checklist / What You Must Do**" section.
⚠ Every answer must follow this structure:

🧾 **Quick Checklist / What You Must Do**
* [5-7 clear, actionable bullet points in plain English]
* [Direct instructions, no legal jargon]

🏗️ **Context & Relevance**
* [Explain why this legal issue matters in neutral terms. Do not invent a startup, SaaS, data, or founder context unless the query includes it.]

⚖️ **Key Legal Requirements**
* [1-2 key laws explained simply with citations]

🔥 **Risks to Manage**
* [Specific penalties or business risks]

🛠️ **Next Steps**
* [Practical checklist for implementation]

**Legal Position:** ✅ Settled Law / ⚖️ Divergent Views / 🆕 Res Integra
""",

    "procedure_guide": """\
OUTPUT FORMAT - PRACTICAL LEGAL PROCEDURE GUIDE

Start with a direct title. Then use this structure where relevant:

1. Present Legal Position
   - State the current law in plain professional language.
   - Cite exact sections and leading cases.

2. Court / Authority / Jurisdiction
   - Explain where the matter can be filed, heard, replied to, or tracked.
   - If the query involves cheque dishonour, cover NI Act Sections 142(2) and 142A.
   - If the query involves tax, company law, labour, consumer, family, criminal, arbitration, or compliance work, name the proper forum/authority and practical filing route.

3. Step-by-Step Procedure
   - Number each statutory step in filing order.
   - Include limitation periods and trigger dates.

4. Essential Ingredients
   - List what must be pleaded/proved.

5. Burden of Proof / Presumptions
   - Include statutory presumptions and rebuttal standard where relevant.

6. Practical Checklist
   - List documents, evidence, notices, tracking proof, and filing checks.

7. Next Actions
   - Offer concrete follow-up outputs such as draft notice, complaint format, jurisdiction checklist, or filing guide.

8. Advanced Litigation Notes
   - Where relevant, include common defences, common drafting errors, and evidentiary traps.
   - For NI Act Section 138 matters, discuss Sections 143 and 145 where relevant, including summary trial and affidavit evidence.
   - For security cheque queries, analyze whether liability had crystallized, post-dated/security cheque distinction, and cases such as Sampelly Satyanarayana Rao where applicable.

End with: **Legal Position:** Settled Law / Divergent Views / Res Integra.
Do not invent citations. Prefer SCC citations where available.
""",

    "court_strategy": """\
OUTPUT FORMAT - COURT STRATEGY MODE

Start with "**Court Strategy:**".

1. Core Position
   - State the best arguable legal position in 2-3 lines.

2. Leading Authorities
   - Give case names, preferred SCC/SCC OnLine citations where available, and the ratio in one line each.

3. Arguments for Petitioner / Applicant
   - Numbered submissions with statutory anchors and precedent support.

4. Counter-Arguments
   - State the strongest likely opposition points.

5. Rebuttal Strategy
   - Give practical answers to the counter-arguments.

6. Evidence / Documents Needed
   - List documents, pleadings, notices, timelines, and proof gaps.

7. Drafting Watchpoints
   - List common drafting errors and factual traps.

8. Suggested Prayer / Relief
   - Give a concise prayer structure, not a full pleading unless asked.

End with: **Legal Position:** Settled Law / Divergent Views / Res Integra.
""",

    "compliance": """\
OUTPUT FORMAT - COMPLIANCE MODE

Start with "**Compliance Action Plan:**".

1. Applicability
   - Identify who must comply and when.

2. Legal Requirements
   - List governing statutes, rules, notifications, and deadlines.

3. Workflow Checklist
   - Give owner, document, due date/trigger, and evidence to retain.

4. Risk / Penalty
   - Explain consequences of non-compliance without exaggeration.

5. Client / Internal Follow-up
   - Provide questions, missing data points, and next professional actions.

End with: **Legal Position:** Settled Law / Divergent Views / Res Integra.
""",
}


# Statute crosswalk + normalizer live in statute_normalize.py (BNSS 504 is real;
# only CrPC-482→BNSS-504 inherent-powers mis-maps are rewritten to BNSS 528).


def _build_rag_context_block(citations: list[dict[str, Any]]) -> str:
    """Format relevant RAG citations as a labeled context block for Gemini."""
    if not citations:
        return ""
    parts = ["RETRIEVED CONTEXT (prefer over model memory where relevant):"]
    for i, c in enumerate(citations[:6], start=1):
        title = c.get("title") or c.get("reference") or f"Source {i}"
        snippet = c.get("snippet") or c.get("text") or ""
        date = c.get("date") or c.get("published_date") or ""
        source = c.get("source") or ""
        meta = []
        if source:
            meta.append(source)
        if date:
            meta.append(date)
        meta_str = " | ".join(meta)
        entry = f"[R{i}] {title}"
        if meta_str:
            entry += f" ({meta_str})"
        if snippet:
            entry += f"\n     {snippet[:400]}"
        parts.append(entry)
    return "\n".join(parts)


def _build_senior_counsel_prompt(
    query: str,
    format_mode: str,
    rag_context: str,
    today_ist: str,
) -> str:
    format_directive = _FORMAT_DIRECTIVES.get(format_mode, _FORMAT_DIRECTIVES["argument_note"])

    sections: list[str] = [
        _SENIOR_COUNSEL_PERSONA,
        f"Date (IST): {today_ist}",
        _CANONICAL_STATUTE_CROSSWALK,
    ]
    if rag_context:
        sections.append(rag_context)

    sections.append(format_directive)
    sections.append(f"QUERY:\n{query.strip()}")

    return "\n\n".join(sections)


# ─── Citation Relevance Filter ────────────────────────────────────────────────

_LEGAL_QUERY_WORD_RE = re.compile(r"[a-z0-9]+")
_LEGAL_QUERY_STOPWORDS = {
    "what", "which", "when", "where", "who", "whom", "whose",
    "why", "how", "is", "are", "was", "were", "do", "does",
    "did", "can", "could", "should", "would", "please", "explain",
    "briefly", "about", "tell", "me", "the", "for", "and", "with",
    "a", "an", "of", "in", "on", "to", "by", "as", "or", "if",
    "this", "that", "these", "those", "be", "been", "being",
    "have", "has", "had", "from", "any", "all", "there", "here",
    "under", "over", "into", "per", "via", "than", "then",
}


def _extract_meaningful_query_terms(query: str) -> set[str]:
    tokens = set(_LEGAL_QUERY_WORD_RE.findall((query or "").lower()))
    return {t for t in tokens if len(t) >= 4 and t not in _LEGAL_QUERY_STOPWORDS}


def _citation_is_relevant(citation: dict[str, Any], query_terms: set[str]) -> tuple[bool, int, float]:
    """Return (relevant, overlap_count, overlap_ratio) for a single citation.

    Relevance rule: at least 2 meaningful query terms must appear in the citation's
    snippet/title/legal-metadata/reference, OR at least 30% of meaningful terms
    overlap.

    If the citation exposes no inspectable content, treat as relevant (stubs in tests).
    """
    if not query_terms:
        return (True, 0, 1.0)

    haystack_parts: list[str] = []
    for key in ("snippet", "title"):
        val = citation.get(key)
        if val:
            haystack_parts.append(str(val))
    legal_meta = citation.get("legal_metadata") or {}
    if isinstance(legal_meta, dict):
        for val in legal_meta.values():
            if val:
                haystack_parts.append(str(val))

    haystack = " ".join(haystack_parts).lower().strip()
    if not haystack:
        return (True, 0, 1.0)

    haystack_tokens = set(_LEGAL_QUERY_WORD_RE.findall(haystack))
    hits = query_terms.intersection(haystack_tokens)
    ratio = len(hits) / max(len(query_terms), 1)

    relevant = len(hits) >= 2 or ratio >= 0.30
    return (relevant, len(hits), ratio)


def _filter_citations_by_relevance(
    citations: list[dict[str, Any]], query: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split citations into (relevant, dropped)."""
    query_terms = _extract_meaningful_query_terms(query)
    if not query_terms:
        return (list(citations), [])

    relevant: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for c in citations:
        is_rel, hits, ratio = _citation_is_relevant(c, query_terms)
        if is_rel:
            relevant.append(c)
        else:
            _logger.debug(
                "citation_dropped title=%r hits=%d ratio=%.2f",
                c.get("title") or c.get("reference") or "?", hits, ratio,
            )
            dropped.append(c)
    return (relevant, dropped)


# ─── Gemini API Call ──────────────────────────────────────────────────────────

async def _call_gemini_text(*, prompt: str, max_tokens: int, temperature: float = 0.2) -> str | None:
    settings = get_settings()
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        _logger.warning("gemini_call skipped: GEMINI_API_KEY not configured")
        return None

    api_base = settings.RAG_GEMINI_API_BASE.rstrip("/")
    model = settings.LEGAL_FALLBACK_GEMINI_MODEL

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.9,
            # Disable Gemini 2.5 Flash's internal "thinking" budget.
            # Without this, the model consumes most of maxOutputTokens on hidden
            # chain-of-thought reasoning, leaving only ~200 visible tokens — which
            # causes mid-sentence truncation on structured legal responses.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    url = f"{api_base}/models/{model}:generateContent"
    _logger.info(
        "gemini_call start model=%s prompt_len=%d max_tokens=%d temperature=%.2f",
        model, len(prompt), max_tokens, temperature,
    )
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)

        if response.status_code >= 400:
            body_excerpt = (response.text or "")[:500]
            _logger.error(
                "gemini_call http_error status=%d model=%s body=%s",
                response.status_code, model, body_excerpt,
            )
            return None

        body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            prompt_feedback = body.get("promptFeedback") or {}
            _logger.warning(
                "gemini_call empty_candidates model=%s promptFeedback=%s",
                model, prompt_feedback,
            )
            return None

        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        text = "\n".join(
            str(part.get("text") or "") for part in parts if isinstance(part, dict)
        ).strip()
        if not text:
            finish_reason = (candidates[0] or {}).get("finishReason")
            _logger.warning(
                "gemini_call empty_text model=%s finishReason=%s", model, finish_reason
            )
            return None

        _logger.info("gemini_call ok model=%s response_len=%d", model, len(text))
        return text
    except Exception as exc:
        _logger.exception("gemini_call exception model=%s err=%s", model, exc)
        return None


async def _call_claude_legal_counsel_text(*, prompt: str, max_tokens: int, temperature: float = 0.2) -> str | None:
    settings = get_settings()
    if not settings.CLAUDE_LEGAL_COUNSEL_ENABLED:
        return None

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        _logger.warning("claude_legal_counsel skipped: ANTHROPIC_API_KEY not configured")
        return None

    api_base = settings.ANTHROPIC_API_BASE.rstrip("/")
    model = settings.CLAUDE_LEGAL_COUNSEL_MODEL
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": (
            "You are Claude Legal Counsel operating inside LegalMitra for Indian legal research, "
            "drafting, and compliance support. Preserve client confidentiality, provide source-aware "
            "answers, avoid hallucinated citations, and require human advocate review before filing "
            "or final legal advice."
        ),
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    _logger.info(
        "claude_legal_counsel start model=%s prompt_len=%d max_tokens=%d temperature=%.2f",
        model, len(prompt), max_tokens, temperature,
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{api_base}/messages", headers=headers, json=payload)

        if response.status_code >= 400:
            body_excerpt = (response.text or "")[:500]
            _logger.error(
                "claude_legal_counsel http_error status=%d model=%s body=%s",
                response.status_code, model, body_excerpt,
            )
            return None

        body = response.json()
        content = body.get("content") or []
        text = "\n".join(
            str(part.get("text") or "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
        if not text:
            _logger.warning("claude_legal_counsel empty_text model=%s", model)
            return None

        _logger.info("claude_legal_counsel ok model=%s response_len=%d", model, len(text))
        return text
    except Exception as exc:
        _logger.exception("claude_legal_counsel exception model=%s err=%s", model, exc)
        return None


def validate_legal_hallucinations(response_text: str) -> str:
    """
    Checks for common legal hallucinations (like IT Act being replaced by BNSS)
    and applies corrections to the final response text.
    """
    corrections = [
        # Hallucination: IT Act is replaced by BNSS
        (
            r"IT Act.*replaced by.*BNSS",
            "Note: The Information Technology Act, 2000 remains in full force and is NOT replaced by BNSS 2023 (which replaces the CrPC)."
        ),
        (
            r"Section 79.*BNSS",
            "Note: Section 79 (Intermediary Safe Harbor) belongs to the IT Act 2000, not BNSS."
        ),
        (
            r"BNSS.*intermediary",
            "Note: BNSS governs criminal procedure; intermediary liability is governed by the IT Act 2000."
        ),
    ]

    fixed_text = response_text
    for pattern, warning in corrections:
        if re.search(pattern, fixed_text, re.IGNORECASE):
            # If we find the hallucination, we append the warning at the end of the paragraph or document
            fixed_text += f"\n\n> [!CAUTION]\n> **Accuracy Alert:** {warning}"

    return fixed_text


# ─── Main Response Builder ────────────────────────────────────────────────────

def _finalize_offline_or_payload(
    *,
    question: str,
    payload: dict[str, Any],
    jurisdiction: str | None,
    missing_jurisdiction: bool = False,
) -> dict[str, Any]:
    return apply_research_trust_layers(
        finalize_research_response(
            question=question,
            response=str(payload.get("response") or ""),
            citations=list(payload.get("citations") or []),
            strategy=str(payload.get("strategy") or "offline"),
            provider=payload.get("provider"),
            note=payload.get("note"),
            dropped_citation_count=int(payload.get("dropped_citation_count") or 0),
            jurisdiction=jurisdiction,
            missing_jurisdiction=missing_jurisdiction,
        )
    )


async def build_hybrid_legal_response(
    *,
    tenant_id: str,
    app_key: str,
    query: str,
    query_type: str = "research",
    rag_result: dict[str, Any],
    background_tasks: BackgroundTasks | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    current_query = extract_current_legal_query(query)
    citations = list(rag_result.get("citations") or [])

    # Filter RAG citations for relevance — only topically matching ones go into context.
    relevant_citations, dropped_citations = _filter_citations_by_relevance(citations, current_query)
    jurisdiction, missing_jurisdiction = resolve_jurisdiction(current_query)

    query_preview = (current_query or "")[:80]
    _logger.info(
        "hybrid_response tenant=%s app=%s rag_citations=%d relevant=%d dropped=%d jurisdiction=%r missing_jurisdiction=%s query=%r",
        tenant_id,
        app_key,
        len(citations),
        len(relevant_citations),
        len(dropped_citations),
        jurisdiction,
        missing_jurisdiction,
        query_preview,
    )

    if missing_jurisdiction:
        return apply_research_trust_layers(
            missing_jurisdiction_response(
                question=current_query,
                dropped_citation_count=len(dropped_citations),
            )
        )

    if _FABRICATION_REQUEST_RE.search(current_query or ""):
        _logger.info(
            "hybrid_response path=fabrication_refused tenant=%s app=%s query=%r",
            tenant_id,
            app_key,
            query_preview,
        )
        return apply_research_trust_layers(
            insufficient_sources_response(
                question=current_query,
                jurisdiction=jurisdiction,
                dropped_citation_count=len(dropped_citations),
                note="Refused fabrication / unpublished-authority request under Stage 2 contract.",
            )
        )

    # Enqueue low-confidence queries for background sync regardless of provider outcome.
    if not relevant_citations and background_tasks is not None:
        background_tasks.add_task(
            enqueue_auto_sync_query,
            tenant_id=tenant_id,
            app_key=app_key,
            query=current_query,
            reason="low_rag_confidence",
        )

    # Deterministic / authorized offline slices (acts list, GST s.54, etc.).
    offline_early = _offline_legal_fallback(current_query, query_type)
    if offline_early and offline_early["strategy"] in {
        "deterministic_indian_acts_list",
        "offline_cgst_section_54_refund_fallback",
        "offline_it_section_139_return_fallback",
    }:
        # Prefer authorized Stage 2 slices even when RAG is empty; acts-list remains early-exit.
        if offline_early["strategy"] == "deterministic_indian_acts_list" or not relevant_citations:
            _logger.info(
                "hybrid_response path=authorized_offline tenant=%s app=%s strategy=%s",
                tenant_id,
                app_key,
                offline_early["strategy"],
            )
            return _finalize_offline_or_payload(
                question=current_query,
                payload=offline_early,
                jurisdiction=jurisdiction or "India (Central)",
            )

    # Stage 2 contract: do not present uncited model memory as grounded research.
    if not relevant_citations:
        if offline_early:
            _logger.info(
                "hybrid_response path=offline_fallback_no_rag tenant=%s app=%s strategy=%s",
                tenant_id,
                app_key,
                offline_early["strategy"],
            )
            return _finalize_offline_or_payload(
                question=current_query,
                payload=offline_early,
                jurisdiction=jurisdiction,
            )
        _logger.info(
            "hybrid_response path=insufficient_sources tenant=%s app=%s",
            tenant_id,
            app_key,
        )
        return apply_research_trust_layers(
            insufficient_sources_response(
                question=current_query,
                jurisdiction=jurisdiction,
                dropped_citation_count=len(dropped_citations),
            )
        )

    today_ist = _now_ist().strftime("%d-%m-%Y")
    format_mode = _detect_format_mode(current_query, query_type)
    rag_context = _build_rag_context_block(relevant_citations)

    prompt = _build_senior_counsel_prompt(
        query=current_query,
        format_mode=format_mode,
        rag_context=rag_context,
        today_ist=today_ist,
    )

    claude_answer = await _call_claude_legal_counsel_text(
        prompt=prompt,
        max_tokens=max(settings.LEGAL_FALLBACK_MAX_TOKENS, 4000),
        temperature=0.12,
    )

    audit_refusals: list[dict[str, Any]] = []
    rag_strategy = str(rag_result.get("strategy") or "rag")

    def _try_model_answer(
        *,
        path: str,
        answer: str | None,
        provider: str,
        strategy_suffix: str,
    ) -> dict[str, Any] | None:
        if not answer or not answer.strip():
            return None
        response_text = validate_legal_hallucinations(answer.strip())
        response_text = normalize_verified_statute_mappings(response_text, current_query)
        response_text += _CLOSING_DISCLAIMER
        _logger.info(
            "hybrid_response path=%s tenant=%s app=%s format=%s response_len=%d",
            path,
            tenant_id,
            app_key,
            format_mode,
            len(response_text),
        )
        accepted = accept_or_record_audit_refusal(
            finalize_research_response(
                question=current_query,
                response=response_text,
                citations=relevant_citations,
                strategy=f"{rag_strategy}_{strategy_suffix}",
                provider=provider,
                note=None,
                dropped_citation_count=len(dropped_citations),
                jurisdiction=jurisdiction,
            ),
            last_refused=audit_refusals,
        )
        if accepted is None:
            _logger.warning(
                "hybrid_response path=%s_audit_refused tenant=%s app=%s; trying next fallback",
                path,
                tenant_id,
                app_key,
            )
        return accepted

    accepted = _try_model_answer(
        path="claude_legal_counsel",
        answer=claude_answer,
        provider="claude_legal_counsel",
        strategy_suffix="claude_legal_counsel",
    )
    if accepted is not None:
        return accepted

    gemini_answer = await _call_gemini_text(
        prompt=prompt,
        max_tokens=max(settings.LEGAL_FALLBACK_MAX_TOKENS, 4000),
        temperature=0.15,
    )
    accepted = _try_model_answer(
        path="gemini",
        answer=gemini_answer,
        provider="gemini",
        strategy_suffix="gemini",
    )
    if accepted is not None:
        return accepted

    # Providers unavailable or Stage 2.1 audit refused — use authorized offline fallback.
    offline_fallback = _offline_legal_fallback(current_query, query_type)
    if offline_fallback:
        _logger.warning(
            "hybrid_response path=offline_fallback tenant=%s app=%s strategy=%s",
            tenant_id, app_key, offline_fallback["strategy"],
        )
        return _finalize_offline_or_payload(
            question=current_query,
            payload=offline_fallback,
            jurisdiction=jurisdiction,
        )

    if audit_refusals:
        return audit_refusals[-1]

    _logger.warning(
        "hybrid_response path=provider_unavailable tenant=%s app=%s (no API key or empty response)",
        tenant_id, app_key,
    )
    return apply_research_trust_layers(
        finalize_research_response(
            question=current_query,
            response=(
                "**Advisory Unavailable**\n\n"
                "The AI engine did not return a response for this query. "
                "Retrieved sources were available, but generation failed.\n\n"
                "**Suggested action:** Retry the query, narrow the scope, "
                "or route to a junior for manual research."
            ),
            citations=relevant_citations,
            strategy="provider_unavailable",
            provider=None,
            note="AI engine did not respond — retry or rephrase the query.",
            dropped_citation_count=len(dropped_citations),
            jurisdiction=jurisdiction,
            confidence="low",
            limitations=[
                "Generation provider failed despite retrieved sources.",
                "Manual review of retrieved citations is required.",
            ],
        )
    )
