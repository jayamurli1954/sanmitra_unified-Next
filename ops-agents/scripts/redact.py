"""
Local redaction layer.

Everything that might be sent to the LLM passes through redact() FIRST, on your
own runner, before any network call. The model only ever sees scrubbed text.

Covers the identifiers most likely to appear in SanMitra logs/errors:
emails, Indian phone numbers, PAN, GSTIN, Aadhaar, and long digit runs
(card / account / order numbers). It is deliberately aggressive — over-
redaction is cheap, leakage is not.

This is pattern-based, not magic. It will not catch a customer's name written
in free text. The real defense is upstream: don't log raw PII or full records
in the first place. Treat this as a safety net, not a guarantee.
"""

from __future__ import annotations

import re

# Order matters: structured IDs (GSTIN/PAN/Aadhaar) are matched before the
# generic long-digit rule so they get their specific label.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Email
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.I), "[EMAIL]"),
    # GSTIN: 2-digit state + 10-char PAN + entity + Z + checksum (15 chars)
    (re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b"), "[GSTIN]"),
    # PAN: AAAAA9999A
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    # Aadhaar: 12 digits, optionally space/dash separated in groups of 4
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[AADHAAR]"),
    # Indian mobile: optional +91/0 prefix, then 6-9 + 9 digits, allowing one
    # space/dash inside the 10-digit body (e.g. "98765 43210").
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[PHONE]"),
    # Generic long digit run (cards, account numbers, order ids): 11-19 digits
    (re.compile(r"(?<!\d)\d{11,19}(?!\d)"), "[NUMBER]"),
    # IPv4
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
]


def redact(text: str) -> str:
    """Return text with sensitive identifiers replaced by typed placeholders."""
    if not text:
        return text
    for pattern, label in _PATTERNS:
        text = pattern.sub(label, text)
    return text


def redact_lines(lines: list[str]) -> list[str]:
    return [redact(line) for line in lines]


if __name__ == "__main__":
    # Quick self-check. Run: python ops-agents/scripts/redact.py
    sample = (
        "User ravi@example.com (PAN ABCDE1234F, GSTIN 29ABCDE1234F1Z5) "
        "called from +91 98765 43210 about invoice, card 4111111111111111, "
        "Aadhaar 1234 5678 9012, from host 10.0.0.14"
    )
    print("BEFORE:", sample)
    print("AFTER :", redact(sample))
