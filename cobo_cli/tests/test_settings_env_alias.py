from cobo_cli.utils.config import CoboSettings


def test_config_file_keys_still_load_by_field_name():
    """The config file loads by field name; validation_alias must not break it."""
    settings = CoboSettings.model_validate(
        {
            "environment": "dev",
            "auth_method": "apikey",
            "api_key": "k1",
            "api_secret": "s1",
        }
    )
    assert (settings.environment, settings.api_key, settings.api_secret) == (
        "dev",
        "k1",
        "s1",
    )


def test_documented_env_vars_take_effect(monkeypatch):
    """The COBO_* variables declared in the source must actually be read.

    They previously used pydantic v1's `Field(env=...)`, which pydantic-settings
    v2 silently ignores, so the variables that really worked were the bare field
    names (API_KEY, ...) - contradicting the source.
    """
    monkeypatch.setenv("COBO_ENVIRONMENT", "prod")
    monkeypatch.setenv("COBO_AUTH_METHOD", "apikey")
    monkeypatch.setenv("COBO_API_KEY", "from-env")
    monkeypatch.setenv("COBO_API_SECRET", "secret-from-env")

    settings = CoboSettings()

    assert settings.environment == "prod"
    assert settings.api_key == "from-env"
    assert settings.api_secret == "secret-from-env"
