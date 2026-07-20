"""MandirMitra actor identity helper for audit and created_by fields."""
from __future__ import annotations

from typing import Any


def _mandir_actor_id(current_user: dict[str, Any]) -> str:
    return str(
        current_user.get("sub")
        or current_user.get("user_id")
        or current_user.get("email")
        or "mandir_compat_system"
    )
