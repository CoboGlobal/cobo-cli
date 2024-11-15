import json
import logging
import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from cobo_cli.cli import cli
from cobo_cli.utils.config import default_manifest_file, user_access_token_key

logger = logging.getLogger(__name__)


class TestAppsCommands(unittest.TestCase):
    def setUp(self):
        logging.getLogger().setLevel(logging.DEBUG)
        self.runner = CliRunner()
        self.mock_app_id = "1234"

        # Setup test manifest data

        self.manifest_data = {
            "app_name": "test-permission-test",
            "app_id": "",
            "dev_app_id": "",
            "callback_urls": ["https://callback.cobo.com/index"],
            "app_desc": "trade on exchanges without worrying about counterparty risks.",
            "app_icon_url": "https://icon.cobo.com/test.svg",
            "homepage_url": "http://127.0.0.1:5000",
            "policy_url": "https://policy.cobo.com",
            "app_key": "1234567890123456789012345678901234567890123456789012345678901234",
            "app_desc_long": "app-description-long",
            "tags": ["Cobo"],
            "screen_shots": [
                "https://icon.cobo.com/screen1.svg",
                "https://icon.cobo.com/screen2.svg",
                "https://icon.cobo.com/screen3.svg",
            ],
            "creator_name": "Cobo",
            "contact_email": "developer@cobo.com",
            "support_site_url": "https://cobo.com/support",
            "permission_notice": "Once installed, this app will be permitted access to your Cobo data as described below.",
            "required_permissions": [
                "mpc_organization_controlled_wallet:stake",
                "custodial_asset_wallet:withdraw",
            ],
            "optional_permissions": ["custodial_asset_wallet:withdraw"],
        }

    def setup_test_environment(self, **kwargs):
        """Helper method to setup test filesystem and manifest"""
        cwd = os.getcwd()
        env_file = f"{cwd}/.cobo_cli.env"
        manifest_file = f"{cwd}/{default_manifest_file}"

        copy_manifest_data = self.manifest_data.copy()
        copy_manifest_data.update(kwargs)
        with open(manifest_file, "w") as f:
            json.dump(copy_manifest_data, f, indent=4)

        return env_file

    @patch("cobo_cli.utils.api.make_request")
    @patch("cobo_cli.utils.config.ConfigManager.get_config")
    def test_app_upload(self, mock_get_config, mock_make_request):
        """Test the app upload command"""

        def mock_get_config_side_effect(key):
            return {
                user_access_token_key: "1234567890123456789012345678901234567890123456789012345678901234",
                "auth_method": "apikey",
            }.get(key)

        mock_get_config.side_effect = mock_get_config_side_effect
        mock_make_request.return_value.status_code = 201
        mock_make_request.return_value.json.return_value = {
            "success": True,
            "result": {"app_id": self.mock_app_id},
        }

        with self.runner.isolated_filesystem():
            env_file = self.setup_test_environment()
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--config-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "app",
                    "upload",
                ],
            )

            self.assertEqual(
                result.exit_code, 0, f"Upload command failed with: {result.output}"
            )
            self.assertIn(
                f"App uploaded successfully with app_id: {self.mock_app_id}",
                result.output,
                "Expected upload success message not found in output",
            )

    @patch("cobo_cli.utils.api.make_request")
    def test_app_update(self, mock_make_request):
        """Test the app update command"""
        mock_make_request.return_value.status_code = 200
        mock_make_request.return_value.json.return_value = {
            "success": True,
            "result": {"app_id": self.mock_app_id},
        }

        with self.runner.isolated_filesystem():
            env_file = self.setup_test_environment(dev_app_id=self.mock_app_id)
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--config-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "app",
                    "update",
                ],
            )

            self.assertEqual(
                result.exit_code, 0, f"Update command failed with: {result.output}"
            )
            self.assertIn(
                f"App updated successfully with app_id: {self.mock_app_id}",
                result.output,
                "Expected update success message not found in output",
            )

    @patch("cobo_cli.utils.api.make_request")
    def test_app_status(self, mock_make_request):
        """Test the app status command"""
        mock_make_request.return_value.status_code = 200
        mock_make_request.return_value.json.return_value = {
            "success": True,
            "result": {"app_id": self.mock_app_id, "status": "APPROVED"},
        }

        with self.runner.isolated_filesystem():
            env_file = self.setup_test_environment(dev_app_id=self.mock_app_id)
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "--config-file",
                    env_file,
                    "--env",
                    "sandbox",
                    "app",
                    "status",
                ],
            )

            self.assertEqual(
                result.exit_code, 0, f"Status command failed with: {result.output}"
            )
            self.assertIn(
                f"app_id: {self.mock_app_id}, status: APPROVED",
                result.output,
                "Expected status message not found in output",
            )

    def test_app_init(self):
        """Test app init command"""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "app",
                    "init",
                    "--app-type",
                    "web",
                    "--backend",
                    "fastapi",
                    "--wallet-type",
                    "custodial-web3",
                    "--auth",
                    "apikey",
                    "--web",
                    "react",
                    "-d",
                    "my-test-app",
                ],
            )

            self.assertEqual(
                result.exit_code, 0, f"Init command failed with: {result.output}"
            )
            self.assertIn("Successfully created", result.output)

            # 验证项目结构
            project_dir = "my-test-app"
            self.assertTrue(os.path.exists(project_dir))
            self.assertTrue(os.path.exists(os.path.join(project_dir, "backend")))

    def test_app_template(self):
        """Test app test-template command"""
        with self.runner.isolated_filesystem():
            # 创建测试目录结构
            os.makedirs("test-project/app/api")
            os.makedirs("test-project/app/services")

            router_content = """
# %if app_type == portal
@router.get("/portal")
async def portal_route():
    return {"message": "Portal route"}
# %endif

# %if wallet_type == custodial-web3
@router.get("/custodial-web3")
async def custodial_route():
    return {"message": "Custodial route"}
# %endif"""

            # 创建测试文件
            with open("test-project/app/api/routes.py", "w") as f:
                f.write(router_content)

            with open("test-project/.code_gen.yaml", "w") as f:
                f.write(
                    """
"app/":
  - app_type:
      - portal
      - web
  - wallet_type:
      - custodial-web3
      - mpc-org-controlled
"""
                )

            # 测试 portal + custodial 组合
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "app",
                    "test-template",
                    "test-project",
                    "--app-type",
                    "portal",
                    "--wallet-type",
                    "custodial-web3",
                    "--auth",
                    "apikey",
                ],
            )

            self.assertEqual(
                result.exit_code, 0, f"Template test failed with: {result.output}"
            )
            self.assertIn('@router.get("/portal")', result.output)
            self.assertIn('@router.get("/custodial-web3")', result.output)

            with open("test-project/app/api/routes.py", "w") as f:
                f.write(router_content)
            # 测试 web + custodial 组合（应该删除 portal 相关代码）
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "app",
                    "test-template",
                    "test-project",
                    "--app-type",
                    "web",
                    "--wallet-type",
                    "custodial-web3",
                    "--auth",
                    "apikey",
                ],
            )

            self.assertEqual(result.exit_code, 0)
            self.assertNotIn('@router.get("/portal")', result.output)
            self.assertIn('@router.get("/custodial-web3")', result.output)

    def test_app_template_errors(self):
        """Test error handling in app test-template command"""
        with self.runner.isolated_filesystem():
            # 测试不存在的目录
            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "app",
                    "test-template",
                    "nonexistent",
                    "--app-type",
                    "web",
                    "--wallet-type",
                    "custodial-web3",
                    "--auth",
                    "apikey",
                ],
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Path 'nonexistent' does not exist", result.output)

            # 测试无效的配置组合
            os.makedirs("test-project")
            with open("test-project/.code_gen.yaml", "w") as f:
                f.write(
                    """
"app/":
  - app_type:
      - portal
  - wallet_type:
      - custodial
"""
                )

            result = self.runner.invoke(
                cli,
                [
                    "--enable-debug",
                    "app",
                    "test-template",
                    "test-project",
                    "--app-type",
                    "portal",
                    "--wallet-type",
                    "mpc",  # 不支持的钱包类型
                    "--auth",
                    "apikey",
                ],
            )

            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Invalid value for '--wallet-type'", result.output)
