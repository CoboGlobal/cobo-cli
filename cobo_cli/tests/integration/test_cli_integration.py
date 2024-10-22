from cobo_cli.cli import cli

def test_logout_command(cli_runner):
    # First, set some dummy tokens
    cli_runner.invoke(cli, ["config", "set", "USER_ACCESS_TOKEN", "dummy_user_token"])
    cli_runner.invoke(cli, ["config", "set", "ORG_ACCESS_TOKEN", "dummy_org_token"])

    # Test logout all
    result = cli_runner.invoke(cli, ["logout"])
    assert result.exit_code == 0
    assert "All access tokens removed." in result.output

    # Verify tokens are removed
    result = cli_runner.invoke(cli, ["config", "get", "USER_ACCESS_TOKEN"])
    assert result.output.strip() == "Configuration 'USER_ACCESS_TOKEN' not found"
    result = cli_runner.invoke(cli, ["config", "get", "ORG_ACCESS_TOKEN"])
    assert result.output.strip() == "Configuration 'ORG_ACCESS_TOKEN' not found"

    # Test user logout
    cli_runner.invoke(cli, ["config", "set", "USER_ACCESS_TOKEN", "dummy_user_token"])
    cli_runner.invoke(cli, ["config", "set", "ORG_ACCESS_TOKEN", "dummy_org_token"])
    result = cli_runner.invoke(cli, ["logout", "-u"])
    assert result.exit_code == 0
    assert "User access token removed." in result.output
    result = cli_runner.invoke(cli, ["config", "get", "ORG_ACCESS_TOKEN"])
    assert result.output.strip() == "ORG_ACCESS_TOKEN: dummy_org_token"
    result = cli_runner.invoke(cli, ["config", "get", "USER_ACCESS_TOKEN"])
    assert result.output.strip() == "Configuration 'USER_ACCESS_TOKEN' not found"

    # Test org logout
    cli_runner.invoke(cli, ["config", "set", "USER_ACCESS_TOKEN", "dummy_user_token"])
    result = cli_runner.invoke(cli, ["logout", "-o"])
    assert result.exit_code == 0
    assert "Organization access token removed." in result.output
    result = cli_runner.invoke(cli, ["config", "get", "USER_ACCESS_TOKEN"])
    assert result.output.strip() == "USER_ACCESS_TOKEN: dummy_user_token"
    result = cli_runner.invoke(cli, ["config", "get", "ORG_ACCESS_TOKEN"])
    assert result.output.strip() == "Configuration 'ORG_ACCESS_TOKEN' not found"
