def test_settings_load():
    from app.core.config import settings
    assert settings.APP_NAME
    assert settings.DATABASE_URL
