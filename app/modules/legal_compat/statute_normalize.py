"""Deterministic high-risk Indian statute crosswalk corrections.

BNSS Section 504 is a real provision (seized-property / no-claimant procedure).
It must NOT be treated as fabricated. What is wrong is mapping CrPC Section 482
(inherent powers / FIR quashing) to BNSS Section 504 — that route is BNSS 528.
Old IPC Section 504 (intentional insult) maps to BNS Section 352.

Curated pair registry: data/legal_seed/india_criminal_code_crosswalk_v1.json
Lookup API helpers: app/modules/legal_compat/code_crosswalk.py
"""
from __future__ import annotations

import re

from app.modules.legal_compat.code_crosswalk import prompt_crosswalk_snippet

CANONICAL_STATUTE_CROSSWALK = """\
CANONICAL STATUTE CROSSWALK - MUST VERIFY BEFORE FINAL ANSWER
1. CrPC Section 482 (saving of inherent powers of High Court; FIR/proceeding quashing) maps to BNSS Section 528.
   - Do NOT map CrPC Section 482 to BNSS Section 504, 538, or any other BNSS section for this route.
   - BNSS Section 504 is a real, different provision (procedure when no claimant appears for seized property within six months; Magistrate may place property at State Government disposal). It is NOT the CrPC 482 successor.
   - Old IPC Section 504 (intentional insult to provoke breach of peace) maps to BNS Section 352 — do not confuse IPC 504 with BNSS 504.
2. IPC Section 420 (cheating and dishonestly inducing delivery of property) maps broadly to BNS Section 318.
3. If the answer discusses FIR quashing, inherent powers, civil dispute dressed as cheating, matrimonial settlement quashing, or abuse of process, use BNSS Section 528 for the inherent-powers route.
4. If unsure about a new-code section number, say verification is required instead of inventing a number.
5. NI Act Section 138 territorial jurisdiction:
   - If the cheque is delivered for collection through an account, apply NI Act Section 142(2)(a): jurisdiction is generally where the payee/holder's bank branch is situated.
   - If the cheque is presented otherwise than through an account, apply NI Act Section 142(2)(b): jurisdiction is generally where the drawee bank branch is situated.
   - Do NOT state a blanket drawee-bank-only rule after the 2015 amendment.
""" + "\n" + prompt_crosswalk_snippet(max_rows=10)

# Only rewrite these when the query/answer is about CrPC 482 / inherent-power quashing.
_WRONG_BNSS_482_PATTERNS = [
    re.compile(r"\bSection\s+504\s+BNSS\b", re.IGNORECASE),
    re.compile(r"\bBNSS\s+Section\s+504\b", re.IGNORECASE),
    re.compile(r"\bSection\s+538\s+BNSS\b", re.IGNORECASE),
    re.compile(r"\bBNSS\s+Section\s+538\b", re.IGNORECASE),
]
_IPC_504_TO_BNSS_504_PATTERN = re.compile(
    r"\b(?:IPC\s+(?:Section\s+)?504|Section\s+504\s+IPC)\b"
    r".{0,60}"
    r"\b(?:is now|maps to|mapped to|replaced by|corresponds to|now)\b"
    r".{0,40}"
    r"\b(?:BNSS\s+(?:Section\s+)?504|Section\s+504\s+BNSS)\b",
    re.IGNORECASE | re.DOTALL,
)
_SECTION_138_EXCLUSIVE_DRAWEE_BANK_PATTERN = re.compile(
    r"(must|shall|only|exclusively).{0,80}(filed|jurisdiction|court).{0,120}drawee\s+bank",
    re.IGNORECASE | re.DOTALL,
)


def _references_crpc_482_or_inherent_quashing(text: str) -> bool:
    lower = (text or "").lower()
    return (
        "section 482" in lower
        or "crpc 482" in lower
        or ("inherent power" in lower and ("quash" in lower or "quashing" in lower))
        or ("saving of inherent powers" in lower and "high court" in lower)
    )


def normalize_verified_statute_mappings(response_text: str, query: str = "") -> str:
    """Apply deterministic high-risk statute crosswalk corrections.

    Rewrites BNSS 504/538 to BNSS 528 only in CrPC-482 / inherent-powers context.
    Leaves genuine BNSS 504 seized-property answers unchanged.
    Corrects explicit IPC 504 -> BNSS 504 claims to BNS 352.
    """
    if not response_text:
        return response_text

    haystack = f"{query}\n{response_text}"
    corrected = response_text
    changed = False
    ipc_504_fixed = False

    if _references_crpc_482_or_inherent_quashing(haystack):
        for pattern in _WRONG_BNSS_482_PATTERNS:
            corrected, count = pattern.subn("Section 528 BNSS", corrected)
            changed = changed or count > 0

    if _IPC_504_TO_BNSS_504_PATTERN.search(corrected):
        corrected, count = _IPC_504_TO_BNSS_504_PATTERN.subn(
            "IPC Section 504 maps to BNS Section 352",
            corrected,
        )
        ipc_504_fixed = count > 0

    if changed and "CrPC Section 482 maps to BNSS Section 528" not in corrected:
        corrected += (
            "\n\n> [!CAUTION]\n"
            "> **Statute Verification:** CrPC Section 482 maps to BNSS Section 528 "
            "for saving of inherent powers of the High Court. Do not treat BNSS "
            "seized-property procedure (distinct from this route) or BNSS s.538 as "
            "the CrPC 482 successor. The answer above has been normalized to "
            "Section 528 BNSS."
        )

    if ipc_504_fixed and "IPC Section 504 (intentional insult) maps to" not in corrected:
        corrected += (
            "\n\n> [!CAUTION]\n"
            "> **Statute Verification:** IPC Section 504 (intentional insult) maps to "
            "BNS Section 352. BNSS Section 504 is a different seized-property procedure "
            "and is not the IPC 504 successor."
        )

    lower_haystack = haystack.lower()
    if (
        ("section 138" in lower_haystack or "cheque" in lower_haystack or "dishonour" in lower_haystack)
        and _SECTION_138_EXCLUSIVE_DRAWEE_BANK_PATTERN.search(corrected)
        and "NI Act Section 138 territorial jurisdiction" not in corrected
    ):
        corrected += (
            "\n\n> [!CAUTION]\n"
            "> **Statute Verification:** NI Act Section 142(2) distinguishes cheque "
            "delivery through an account from direct presentation. For collection "
            "through the payee/holder's account, jurisdiction is generally where the "
            "payee/holder's bank branch is situated; drawee-bank jurisdiction applies "
            "where the cheque is presented otherwise than through an account."
        )

    return corrected
