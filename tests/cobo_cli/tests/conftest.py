import pytest
from click.testing import CliRunner

from cobo_cli.cli import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def invoke_cli(cli_runner):
    def _invoke_cli(*args, **kwargs):
        return cli_runner.invoke(cli, *args, **kwargs)

    return _invoke_cli
