import json
import logging
import os
import unittest
from unittest.mock import patch

import click
from click.testing import CliRunner

from cobo_cli.cli import cli
from cobo_cli.managers.config_manager import default_manifest_file
from cobo_cli.utils.portal_client import ApiResponse, PortalClient

logger = logging.getLogger(__name__)


class TestAppsCommands(unittest.TestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)

    @patch.object(PortalClient, "get_status")
    @patch.object(PortalClient, "update_app")
    @patch.object(PortalClient, "publish_app")
    def test_app_publish(self, publish_app, update_app, get_status):
        runner = CliRunner()
        publish_app.return_value = ApiResponse(
            success=True, result={"app_id": "1234"}, exception=None
        )
        update_app.return_value = ApiResponse(
            success=True, result={"app_id": "1234"}, exception=None
        )
        get_status.return_value = ApiResponse(
            success=True,
            result={"app_id": "1234", "status": "APPROVED"},
            exception=None,
        )
        assert isinstance(cli, click.Group)
        with runner.isolated_filesystem():
            cwd = os.getcwd()
            env_file = f"{cwd}/.cobo_cli.env"
            manifest_file = f"{cwd}/{default_manifest_file}"
            manifest_data = {
                "app_name": "jw-test-permission-test",
                "app_id": None,
                "dev_app_id": "",
                "callback_urls": ["modify-https://superloop.cobo.com/index"],
                "app_desc": "trade on exchanges without worrying about counterparty risks.",
                "app_icon_url": "modify-https://d.cobo.com/public/logos/Icon_SuperLoop.svg",
                "homepage_url": "http://127.0.0.1",
                "policy_url": "modify-https://superloop.cobo.com/privacy",
                "client_key": "modify-1234567890123456789012345678901234567890123456789012345678901234",
                "app_desc_long": "modify-long description",
                "tags": ["modify-Cobo"],
                "screen_shots": [
                    "modify-https://d.cobo.com/apk/android/SuperLoop.png",
                    "https://d.cobo.com/apk/android/Loop.png",
                    "https://d.cobo.com/apk/android/MirrorModal.png",
                ],
                "creator_name": "modify-Cobo",
                "contact_email": "jingwen.wang+portal1modify@cobo.com",
                "support_site_url": "modify-https://superloop.cobo.com/support",
                "permission_notice": "modify-Once installed, Superloop will be permitted access to your Cobo data as described below.",
                "required_permissions": [
                    "mpc_organization_controlled_wallet,stake",
                    "custodial_asset_wallet,withdraw",
                ],
                "optional_permissions": ["custodial_asset_wallet,withdraw"],
                "framework": "fastapi",
            }

            # 写入 JSON 数据到 manifest_file
            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f, indent=4)

            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--env-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "apps",
                    "publish",
                ],
            )
            logger.info(f"command result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(
                "App published successfully with app_id: 1234" in result.output
            )

            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--env-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "apps",
                    "update",
                ],
            )

            logger.info(f"command cobo app update result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(
                "App updated successfully with app_id: 1234" in result.output
            )

            result = runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--env-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "apps",
                    "status",
                ],
            )
            logger.info(f"command cobo app status result: {result.output}")
            self.assertEqual(result.exit_code, 0)
            self.assertTrue("app_id: 1234, status: APPROVED" in result.output)
