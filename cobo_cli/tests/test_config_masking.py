import pytest

from cobo_cli.commands.config import mask_if_sensitive


@pytest.mark.parametrize(
    "key",
    ["api_secret", "API_SECRET", "user_access_token", "app_password", "private_key"],
)
def test_sensitive_values_are_masked(key):
    """敏感值不得回显: 终端录屏、日志采集、历史共享都会造成泄漏。"""
    masked = mask_if_sensitive(key, "00112233445566778899aabbccddeeff")
    assert "00112233" not in masked
    assert masked.endswith("eeff")
    assert masked.startswith("*")


def test_short_sensitive_value_is_fully_masked():
    assert mask_if_sensitive("api_secret", "abc") == "***"


@pytest.mark.parametrize("key", ["api_key", "environment", "auth_method", "api_host"])
def test_non_sensitive_values_are_unchanged(key):
    # api_key 是公钥, 需要完整显示以便用户核对已注册的是哪一把
    assert mask_if_sensitive(key, "ae1b2500a647457a") == "ae1b2500a647457a"


def test_non_string_values_are_handled():
    assert mask_if_sensitive("environment", 123) == "123"
