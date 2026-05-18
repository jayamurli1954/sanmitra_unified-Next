from app.config import get_settings


def test_local_frontend_origin_is_allowed_for_static_e2e_shell():
    settings = get_settings()

    assert "http://127.0.0.1:3300" in settings.ALLOWED_ORIGINS
    assert "http://localhost:3300" in settings.ALLOWED_ORIGINS
