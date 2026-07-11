import pytest

from app.core.tenants.context import InvalidAppKeyError, inject_app_key, resolve_app_key, set_app_key, validate_app_key


def test_resolve_app_key_supports_gharmitra_alias() -> None:
    assert resolve_app_key("gharmitra") == "gruhamitra"
    assert resolve_app_key("gruhamitra") == "gruhamitra"


def test_resolve_app_key_rejects_unknown_key() -> None:
    with pytest.raises(InvalidAppKeyError, match="Invalid X-App-Key header"):
        resolve_app_key("not-a-real-app")


def test_validate_app_key_rejects_unknown_key() -> None:
    with pytest.raises(InvalidAppKeyError, match="Invalid X-App-Key header"):
        validate_app_key("not-a-real-app")


@pytest.mark.asyncio
async def test_inject_app_key_rejects_invalid_header_even_when_context_has_default() -> None:
    set_app_key("mandirmitra")

    with pytest.raises(InvalidAppKeyError, match="Invalid X-App-Key header"):
        await inject_app_key("not-a-real-app")


@pytest.mark.asyncio
async def test_inject_app_key_prefers_valid_header_over_context_default() -> None:
    set_app_key("mandirmitra")

    assert await inject_app_key("mitrabooks") == "mitrabooks"
