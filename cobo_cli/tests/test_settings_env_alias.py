from cobo_cli.utils.config import CoboSettings


def test_config_file_keys_still_load_by_field_name():
    """配置文件按字段名加载 —— validation_alias 不得破坏这条路径。"""
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
    """源码声明的 COBO_* 环境变量此前使用 pydantic v1 的 env= 参数,
    在 pydantic-settings v2 下被静默忽略, 实际生效的是裸 API_KEY —— 与声明不符。
    """
    monkeypatch.setenv("COBO_ENVIRONMENT", "prod")
    monkeypatch.setenv("COBO_AUTH_METHOD", "apikey")
    monkeypatch.setenv("COBO_API_KEY", "from-env")
    monkeypatch.setenv("COBO_API_SECRET", "secret-from-env")

    settings = CoboSettings()

    assert settings.environment == "prod"
    assert settings.api_key == "from-env"
    assert settings.api_secret == "secret-from-env"
