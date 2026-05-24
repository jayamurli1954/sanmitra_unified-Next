from app.config import get_settings
from app.main import app


def test_local_frontend_origin_is_allowed_for_static_e2e_shell():
    settings = get_settings()

    assert "http://127.0.0.1:3300" in settings.ALLOWED_ORIGINS
    assert "http://localhost:3300" in settings.ALLOWED_ORIGINS


def test_known_vercel_preview_origin_is_allowed_by_cors_regex():
    middleware = next(item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware")
    origin_regex = middleware.kwargs["allow_origin_regex"]

    import re

    assert re.fullmatch(origin_regex, "https://mitrabooks-14kr5spv7-jayamurli1954s-projects.vercel.app")
    assert re.fullmatch(origin_regex, "https://mitrabooks-erp-git-main-jayamurli1954s-projects.vercel.app")
    assert not re.fullmatch(origin_regex, "https://unknown-app-jayamurli1954s-projects.vercel.app")
