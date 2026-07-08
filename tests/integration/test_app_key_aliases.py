import pytest

from app.core.tenants.context import InvalidAppKeyError, resolve_app_key, validate_app_key


def test_resolve_app_key_supports_gharmitra_alias() -> None:
    assert resolve_app_key("gharmitra") == "gruhamitra"
    assert resolve_app_key("gruhamitra") == "gruhamitra"


def test_resolve_app_key_rejects_unknown_key() -> None:
    with pytest.raises(InvalidAppKeyError, match="Invalid X-App-Key header"):
        resolve_app_key("not-a-real-app")


def test_validate_app_key_rejects_unknown_key() -> None:
    with pytest.raises(InvalidAppKeyError, match="Invalid X-App-Key header"):
        validate_app_key("not-a-real-app")
