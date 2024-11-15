from unittest.mock import patch

from cobo_cli.cli import cli
from cobo_cli.utils.config import (
    ConfigManager,
    org_access_token_key,
    user_access_token_key,
)


def test_logout_command(cli_runner):
    # 模拟配置存储
    config_store = {
        "common": {"auth_method": "apikey", "environment": "dev"},
        "sandbox": {
            "api_host": "https://api.sandbox.cobo.com",
            "websocket_host": "wss://api.sandbox.cobo.com",
            "base_url": "https://portal.sandbox.cobo.com",
        },
        "dev": {
            "api_host": "https://api.dev.cobo.com",
            "websocket_host": "wss://api.dev.cobo.com",
            "base_url": "https://portal.dev.cobo.com",
        },
        "prod": {
            "api_host": "https://api.cobo.com",
            "websocket_host": "wss://api.cobo.com",
            "base_url": "https://portal.cobo.com",
        },
    }

    def mock_load_config():
        return config_store

    def mock_save_config():
        pass

    patch.object(
        ConfigManager, "load_config_data", side_effect=mock_load_config
    ).start()

    patch.object(ConfigManager, "save_config", side_effect=mock_save_config).start()

    # First, set some dummy tokens
    result = cli_runner.invoke(
        cli, ["config", "set", user_access_token_key, "dummy_user_token"]
    )
    assert result.exit_code == 0

    result = cli_runner.invoke(
        cli, ["config", "set", org_access_token_key, "dummy_org_token"]
    )
    assert result.exit_code == 0

    # Test logout all
    result = cli_runner.invoke(cli, ["logout"])
    assert result.exit_code == 0
    assert "All access tokens removed." in result.output

    # Verify tokens are removed
    result = cli_runner.invoke(cli, ["config", "get", user_access_token_key])
    assert result.output.strip() == f"Configuration '{user_access_token_key}' not found"
    result = cli_runner.invoke(cli, ["config", "get", org_access_token_key])
    assert result.output.strip() == f"Configuration '{org_access_token_key}' not found"

    # Test user logout
    cli_runner.invoke(cli, ["config", "set", user_access_token_key, "dummy_user_token"])
    cli_runner.invoke(cli, ["config", "set", org_access_token_key, "dummy_org_token"])
    result = cli_runner.invoke(cli, ["logout", "-u"])
    assert result.exit_code == 0
    assert "User access token removed." in result.output
    result = cli_runner.invoke(cli, ["config", "get", org_access_token_key])
    assert result.output.strip() == f"{org_access_token_key}: dummy_org_token"
    result = cli_runner.invoke(cli, ["config", "get", user_access_token_key])
    assert result.output.strip() == f"Configuration '{user_access_token_key}' not found"

    # Test org logout
    cli_runner.invoke(cli, ["config", "set", user_access_token_key, "dummy_user_token"])
    result = cli_runner.invoke(cli, ["logout", "-o"])
    assert result.exit_code == 0
    assert "Organization access token removed." in result.output
    result = cli_runner.invoke(cli, ["config", "get", user_access_token_key])
    assert result.output.strip() == f"{user_access_token_key}: dummy_user_token"
    result = cli_runner.invoke(cli, ["config", "get", org_access_token_key])
    assert result.output.strip() == f"Configuration '{org_access_token_key}' not found"
