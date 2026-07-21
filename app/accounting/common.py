"""Shared accounting primitives (exceptions + scope/quantize helpers).

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

class AccountingValidationError(ValueError):
    pass


class AccountingIdempotencyConflictError(AccountingValidationError):
    pass


class AccountingNotFoundError(ValueError):
    pass


def _money_float(value: Decimal | int | float | str | None) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_key(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def _tokenize(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z0-9]+", value.lower()))
    stop_words = {"the", "and", "for", "with", "account", "ac", "a", "an"}
    return {token for token in tokens if len(token) > 2 and token not in stop_words}


def _match_confidence(score: float) -> Decimal:
    bounded = max(0.0, min(score, 1.0))
    return _q(Decimal(str(bounded)))


def _accounting_scope(model, *, app_key: str, tenant_id: str, accounting_entity_id: str):
    return (
        model.app_key == app_key,
        model.tenant_id == tenant_id,
        model.accounting_entity_id == accounting_entity_id,
    )

