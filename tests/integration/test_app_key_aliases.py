from app.core.tenants.context import resolve_app_key


def test_resolve_app_key_supports_gharmitra_alias() -> None:
    assert resolve_app_key("gharmitra") == "gruhamitra"
    assert resolve_app_key("gruhamitra") == "gruhamitra"

