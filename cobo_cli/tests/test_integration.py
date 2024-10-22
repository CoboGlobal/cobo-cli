import pytest
from click.testing import CliRunner

from cobo_cli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_config_commands(runner):
    result = runner.invoke(cli, ["config", "set", "test_key", "test_value"])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["config", "get", "test_key"])
    assert result.exit_code == 0
    assert "test_value" in result.output


# Add more integration tests for other CLI commands
