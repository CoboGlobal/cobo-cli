import logging
import os
import unittest

import click
from click.testing import CliRunner

from cobo_cli.cli import cli

logger = logging.getLogger(__name__)


class TestConfigCommands(unittest.TestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)

    def test_config_commands(self):
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
                    "config",
                    "set",
                    "num",
                    "100",
                ],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue("Configuration 'num' set to '100'" in result.output)

            result = runner.invoke(
                cli, ["--enable-debug", "--env-file", env_file, "config", "get", "num"]
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue("num: 100" in result.output)

            result = runner.invoke(
                cli,
                ["--enable-debug", "--env-file", env_file, "config", "get", "number"],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)

            self.assertTrue("Configuration 'number' not found" in result.output)

            result = runner.invoke(
                cli,
                ["--enable-debug", "--env-file", env_file, "config", "delete", "num"],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue("Configuration 'num' deleted" in result.output)

            result = runner.invoke(
                cli, ["--enable-debug", "--env-file", env_file, "config", "get", "num"]
            )
            logger.info(f"command result: {result.output}")

            self.assertEqual(result.exit_code, 0)
            self.assertTrue("Configuration 'num' not found" in result.output)
