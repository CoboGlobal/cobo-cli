import logging
import os
import unittest

import click
from click.testing import CliRunner

from cobo_cli.cli import cli

logger = logging.getLogger(__name__)


class TestKeysCommands(unittest.TestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)

    def test_keys_generate(self):
        runner = CliRunner()

        assert isinstance(cli, click.Group)
        with runner.isolated_filesystem():
            cwd = os.getcwd()
            env_file = f"{cwd}/.cobo_cli.env"
            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--env-file",
                    env_file,
                    "keys",
                    "generate",
                ],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)

            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--env-file",
                    env_file,
                    "--env",
                    "prod",
                    "keys",
                    "generate",
                    "--key-type",
                    "APP",
                ],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)
