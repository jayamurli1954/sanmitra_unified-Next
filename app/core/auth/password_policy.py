from __future__ import annotations

from fastapi import HTTPException

MIN_PASSWORD_LENGTH = 10


def validate_password_policy(password: str, *, field_label: str = "Password") -> None:
    value = str(password or "")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"{field_label} must be at least {MIN_PASSWORD_LENGTH} characters long",
        )
    if not any(ch.islower() for ch in value):
        raise HTTPException(status_code=400, detail=f"{field_label} must include at least one lowercase letter")
    if not any(ch.isupper() for ch in value):
        raise HTTPException(status_code=400, detail=f"{field_label} must include at least one uppercase letter")
    if not any(ch.isdigit() for ch in value):
        raise HTTPException(status_code=400, detail=f"{field_label} must include at least one number")
    if not any(not ch.isalnum() for ch in value):
        raise HTTPException(status_code=400, detail=f"{field_label} must include at least one special character")
