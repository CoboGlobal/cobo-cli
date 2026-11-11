import pytest

from cobo_cli.commands.config import mask_if_sensitive


@pytest.mark.parametrize(
    "key",
    ["api_secret", "API_SECRET", "user_access_token", "app_password", "private_key"],
)
def test_sensitive_values_are_masked(key):
    """Sensitive values must not be echoed: recordings, logs and shell history
    all leak them."""
    masked = mask_if_sensitive(key, "00112233445566778899aabbccddeeff")
    assert "00112233" not in masked
    assert masked.endswith("eeff")
    assert masked.startswith("*")


def test_short_sensitive_value_is_fully_masked():
    assert mask_if_sensitive("api_secret", "abc") == "***"


@pytest.mark.parametrize("key", ["api_key", "environment", "auth_method", "api_host"])
def test_non_sensitive_values_are_unchanged(key):
    # api_key is a public key: show it in full so the user can check which one
    # is registered
    assert mask_if_sensitive(key, "ae1b2500a647457a") == "ae1b2500a647457a"


def test_non_string_values_are_handled():
    assert mask_if_sensitive("environment", 123) == "123"
