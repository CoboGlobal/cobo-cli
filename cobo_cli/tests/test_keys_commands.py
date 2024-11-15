import logging
import os
import unittest
from unittest.mock import patch

import click
from click.testing import CliRunner

from cobo_cli.cli import cli

logger = logging.getLogger(__name__)


class TestKeysCommands(unittest.TestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)

    @patch("cobo_cli.commands.keys.handle_app_key_generation")
    def test_keys_generate(self, mock_handle_app_key_generation):
        mock_handle_app_key_generation.return_value = None
        runner = CliRunner()

        assert isinstance(cli, click.Group)
        with runner.isolated_filesystem():
            cwd = os.getcwd()
            env_file = f"{cwd}/.cobo_cli.env"
            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--config-file",
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
                    "--config-file",
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
