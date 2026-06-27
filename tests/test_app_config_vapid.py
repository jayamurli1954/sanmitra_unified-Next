from app.config import Settings


def test_settings_validate_generates_temporary_vapid_keys_when_missing() -> None:
    settings = Settings()
    settings.ENVIRONMENT = "development"
    settings.JWT_SECRET = ""
    settings.VAPID_PUBLIC_KEY = ""
    settings.VAPID_PRIVATE_KEY = ""

    settings.validate()

    assert settings.VAPID_PUBLIC_KEY
    assert settings.VAPID_PRIVATE_KEY
