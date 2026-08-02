from app.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


def test_local_frontend_origin_is_allowed_for_static_e2e_shell():
    settings = get_settings()

    assert "http://127.0.0.1:3300" in settings.ALLOWED_ORIGINS
    assert "http://localhost:3300" in settings.ALLOWED_ORIGINS


def test_mitrabooks_custom_domain_origins_are_allowed():
    settings = get_settings()

    assert "https://mitrabooks.sanmitratech.in" in settings.ALLOWED_ORIGINS
    assert "https://www.mitrabooks.sanmitratech.in" in settings.ALLOWED_ORIGINS


def test_known_vercel_preview_origin_is_allowed_by_cors_regex():
    middleware = next(item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware")
    origin_regex = middleware.kwargs["allow_origin_regex"]

    import re

    assert re.fullmatch(origin_regex, "https://mitrabooks-14kr5spv7-jayamurli1954s-projects.vercel.app")
    assert re.fullmatch(origin_regex, "https://mitrabooks-erp-git-main-jayamurli1954s-projects.vercel.app")
    assert not re.fullmatch(origin_regex, "https://unknown-app-jayamurli1954s-projects.vercel.app")


def test_cors_middleware_is_outside_tenant_context():
    names = [item.cls.__name__ for item in app.user_middleware]
    assert names.index("CORSMiddleware") < names.index("TenantContextMiddleware")


def test_options_preflight_from_local_shell_returns_cors_headers():
    client = TestClient(app)
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3300",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-app-key",
            # Some browsers/extensions attach custom headers on OPTIONS; must not break CORS.
            "X-App-Key": "not-a-real-app",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3300"


def test_options_preflight_for_google_config_allows_local_shell():
    client = TestClient(app)
    response = client.options(
        "/api/v1/auth/google-config",
        headers={
            "Origin": "http://127.0.0.1:3300",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type,x-app-key",
            "X-App-Key": "bogus",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3300"
