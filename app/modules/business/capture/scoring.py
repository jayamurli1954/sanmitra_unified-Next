"""Blended confidence. Validation is a HARD gate, not a weight:

    final = min(required-field confidences) * (1.0 if all checks pass else 0.0)

So a model that self-reports high confidence still scores 0 if any deterministic
check fails — it cannot talk its way past validation.
"""
from __future__ import annotations

from typing import Any

from app.modules.business.capture.extract import REQUIRED_FIELDS

# Tenant-configurable later; conservative default.
AUTO_THRESHOLD = 0.95


def blended_score(field_confidences: dict[str, Any], *, validation_passed: bool) -> float:
    if not validation_passed:
        return 0.0
    vals: list[float] = []
    for key in REQUIRED_FIELDS:
        try:
            vals.append(float(field_confidences.get(key) or 0.0))
        except (TypeError, ValueError):
            vals.append(0.0)
    floor = min(vals) if vals else 0.0
    return round(max(0.0, min(1.0, floor)), 4)


def routed_status(score: float, *, validation_passed: bool) -> str:
    from app.modules.business.capture import models

    if validation_passed and score >= AUTO_THRESHOLD:
        return models.STATUS_DRAFTED
    return models.STATUS_NEEDS_REVIEW
