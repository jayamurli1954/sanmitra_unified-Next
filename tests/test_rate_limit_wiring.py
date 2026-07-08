from app.core.rate_limiting import limiter

# Import routers to ensure decorators register all route limits.
import app.api.legacy_alias_router  # noqa: F401
import app.core.auth.router  # noqa: F401
import app.modules.legal.router  # noqa: F401
import app.modules.business.router  # noqa: F401


def _limits_by_endpoint() -> dict[str, list[str]]:
    return {
        endpoint_name: [str(item.limit) for item in limits]
        for endpoint_name, limits in limiter._route_limits.items()
    }


def test_auth_and_legacy_rate_limits_are_wired() -> None:
    limits = _limits_by_endpoint()

    assert limits["app.core.auth.router.login"] == ["10 per 1 minute"]
    assert limits["app.core.auth.router.local_login"] == ["10 per 1 minute"]
    assert limits["app.core.auth.router.register"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.register_request"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.forgot_password"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.reset_password"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.mobile_otp_send"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.mobile_otp_verify"] == ["10 per 1 minute"]
    assert limits["app.core.auth.router.google_login"] == ["10 per 1 minute"]
    assert limits["app.core.auth.router.activate_account"] == ["5 per 1 minute"]
    assert limits["app.core.auth.router.refresh"] == ["20 per 1 minute"]

    assert limits["app.api.legacy_alias_router.legacy_auth_login"] == ["10 per 1 minute"]
    assert limits["app.api.legacy_alias_router.legacy_auth_local_login"] == ["10 per 1 minute"]
    assert limits["app.api.legacy_alias_router.legacy_auth_register"] == ["5 per 1 minute"]
    assert limits["app.api.legacy_alias_router.legacy_auth_refresh"] == ["20 per 1 minute"]


def test_legal_proxy_rate_limits_are_wired() -> None:
    limits = _limits_by_endpoint()

    assert limits["app.modules.legal.router.get_legal_news"] == ["20 per 1 minute"]
    assert limits["app.modules.legal.router.get_court_judgements"] == ["20 per 1 minute"]
    assert limits["app.modules.legal.router.get_web_search_context"] == ["10 per 1 minute"]


def test_ca_invite_rate_limits_are_wired() -> None:
    limits = _limits_by_endpoint()

    assert limits["app.modules.business.router.preview_ca_invite"] == ["20 per 1 minute"]
    assert limits["app.modules.business.router.accept_ca_invite"] == ["10 per 1 minute"]
