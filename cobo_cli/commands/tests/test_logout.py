import pytest
from click.testing import CliRunner

from cobo_cli.cli import cli


@pytest.fixture
def mock_keys_manager(mocker):
    return mocker.patch("cobo_cli.commands.logout.KeysManager")


def test_logout_all(mock_keys_manager):
    runner = CliRunner()
    result = runner.invoke(cli, ["logout"])
    assert result.exit_code == 0
    assert "All access tokens removed." in result.output
    mock_keys_manager.return_value.remove_user_access_token.assert_called_once()
    mock_keys_manager.return_value.remove_org_access_token.assert_called_once()


def test_logout_user(mock_keys_manager):
    runner = CliRunner()
    result = runner.invoke(cli, ["logout", "-u"])
    assert result.exit_code == 0
    assert "User access token removed." in result.output
    mock_keys_manager.return_value.remove_user_access_token.assert_called_once()
    mock_keys_manager.return_value.remove_org_access_token.assert_not_called()


def test_logout_org(mock_keys_manager):
    runner = CliRunner()
    result = runner.invoke(cli, ["logout", "-o"])
    assert result.exit_code == 0
    assert "Organization access token removed." in result.output
    mock_keys_manager.return_value.remove_user_access_token.assert_not_called()
    mock_keys_manager.return_value.remove_org_access_token.assert_called_once()
