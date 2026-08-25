from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cobo_cli.commands.node import node
from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.utils.config import ConfigManager
from cobo_cli.utils.tss_node import DEFAULT_IMAGE, parse_node_id, relay_state, run_args

NODE_ID = "cobovG5Tzq9keGocMZYtTfDrmevQgQmsYvzoPaEisBJPGXzzN"


def _context(environment="prod"):
    return CommandContext(
        env=EnvironmentType(environment),
        auth_method=AuthMethodType.APIKEY,
        config_manager=ConfigManager(),
        api_spec=None,
    )


def _invoke(args, environment="prod"):
    return CliRunner().invoke(node, args, obj=_context(environment))


class TestRunArgs:
    def test_password_reaches_docker_only_as_a_file_mount(self, tmp_path):
        key = tmp_path / "key"
        key.write_text("SixteenCharsLongPw")
        args = run_args("prod", ["init"], key, DEFAULT_IMAGE)
        assert f"{key}:/app/secret/key:ro" in args
        # The password value itself must never be an argument.
        assert all("SixteenCharsLongPw" not in a for a in args)
        assert args[-2:] == ["--key-file", "/app/secret/key"]

    def test_mounts_all_four_data_dirs(self, tmp_path):
        args = run_args("prod", ["start"], tmp_path / "k", DEFAULT_IMAGE)
        mounts = [a for a in args if a.startswith("/") and ":/app/" in a]
        targets = {m.split(":")[-1] for m in mounts}
        assert {"/app/configs", "/app/db", "/app/logs", "/app/recovery"} <= targets

    def test_detach_names_the_container_and_rm_otherwise(self, tmp_path):
        detached = run_args(
            "prod", ["start"], tmp_path / "k", DEFAULT_IMAGE, detach=True
        )
        assert "-d" in detached and "cobo-tss-node-prod" in detached
        oneshot = run_args("prod", ["init"], tmp_path / "k", DEFAULT_IMAGE)
        assert "--rm" in oneshot and "-d" not in oneshot

    def test_ca_bundle_mount_sets_ssl_cert_file(self, tmp_path):
        ca = tmp_path / "ca.pem"
        args = run_args("prod", ["start"], tmp_path / "k", DEFAULT_IMAGE, ca_bundle=ca)
        assert f"{ca}:/etc/cobo-extra-ca.pem:ro" in args
        assert "SSL_CERT_FILE=/etc/cobo-extra-ca.pem" in args


class TestEnvironmentMapping:
    @pytest.mark.parametrize(
        "environment,node_env",
        [("prod", "production"), ("dev", "development"), ("sandbox", "development")],
    )
    def test_config_written_for_environment(self, tmp_path, environment, node_env):
        with patch("cobo_cli.utils.tss_node.Path.home", return_value=tmp_path):
            from cobo_cli.utils.tss_node import prepare_home

            home = prepare_home(environment)
        config = (home / "configs" / "cobo-tss-node-config.yaml").read_text()
        assert config == f"env: {node_env}\n"

    def test_existing_config_is_not_overwritten(self, tmp_path):
        with patch("cobo_cli.utils.tss_node.Path.home", return_value=tmp_path):
            from cobo_cli.utils.tss_node import prepare_home

            home = prepare_home("prod")
            marker = "env: production\ncallback: {}\n"
            (home / "configs" / "cobo-tss-node-config.yaml").write_text(marker)
            prepare_home("prod")
        assert (home / "configs" / "cobo-tss-node-config.yaml").read_text() == marker


class TestParsing:
    def test_node_id_parsed_from_init_output(self):
        out = f'time=x level=info msg="Initialize Node ID: {NODE_ID} "\nother'
        assert parse_node_id(out) == NODE_ID

    def test_node_id_absent(self):
        assert parse_node_id("no id here") is None

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("[Websocket.Client] connected.", "connected to the relay"),
            (
                "Connection refused, reason: node identity check failed: node x is not bound to any app",
                "waiting to be added",
            ),
            (
                "Connection failed: tls: failed to verify certificate: x509: certificate signed by unknown authority",
                "--ca-bundle",
            ),
        ],
    )
    def test_relay_state_summaries(self, line, expected):
        completed = MagicMock(stdout=f"noise\n{line}\n", stderr="")
        with patch("cobo_cli.utils.tss_node.subprocess.run", return_value=completed):
            assert expected in relay_state("prod")

    def test_latest_line_wins(self):
        logs = (
            "Connection refused, reason: node x is not bound to any app\n"
            "[Websocket.Client] connected.\n"
        )
        completed = MagicMock(stdout=logs, stderr="")
        with patch("cobo_cli.utils.tss_node.subprocess.run", return_value=completed):
            assert relay_state("prod") == "connected to the relay"


class TestCommands:
    def test_init_requires_a_key_file(self, tmp_path):
        with patch("cobo_cli.commands.node.ensure_docker"), patch(
            "cobo_cli.utils.tss_node.Path.home", return_value=tmp_path
        ):
            result = _invoke(["init"])
        assert result.exit_code != 0
        assert "--key-file" in result.output

    def test_init_refuses_to_overwrite_an_existing_identity(self, tmp_path):
        (tmp_path / ".cobo" / "tss-node" / "prod" / "db").mkdir(parents=True)
        (tmp_path / ".cobo" / "tss-node" / "prod" / "db" / "secrets.db").write_text("x")
        with patch("cobo_cli.commands.node.ensure_docker"), patch(
            "cobo_cli.utils.tss_node.Path.home", return_value=tmp_path
        ), patch(
            "cobo_cli.commands.node.node_home",
            return_value=tmp_path / ".cobo" / "tss-node" / "prod",
        ), patch(
            "cobo_cli.commands.node.prepare_home",
            return_value=tmp_path / ".cobo" / "tss-node" / "prod",
        ):
            result = _invoke(["init", "--key-file", "/nonexistent"])
        assert result.exit_code != 0
        assert "already initialized" in result.output

    def test_init_stores_the_node_id_and_says_what_next(self, tmp_path):
        home = tmp_path / ".cobo" / "tss-node" / "prod"
        key = tmp_path / "key"
        key.write_text("SixteenCharsLongPw")
        init_output = f'msg="Initialize Node ID: {NODE_ID} "\nComplete initialization'
        completed = MagicMock(returncode=0, stdout=init_output, stderr="")
        with patch("cobo_cli.commands.node.ensure_docker"), patch(
            "cobo_cli.commands.node.prepare_home", return_value=home
        ), patch("cobo_cli.commands.node._run", return_value=completed), patch(
            "cobo_cli.commands.node.run_args", return_value=["docker"]
        ):
            home.mkdir(parents=True)
            result = _invoke(["init", "--key-file", str(key)])
        assert result.exit_code == 0, result.output
        assert (home / "node_id").read_text().strip() == NODE_ID
        assert NODE_ID in result.output
        assert "Back up" in result.output
        assert "key_share_holder_groups" in result.output

    def test_start_requires_an_initialized_node(self, tmp_path):
        home = tmp_path / ".cobo" / "tss-node" / "prod"
        home.mkdir(parents=True)
        with patch("cobo_cli.commands.node.ensure_docker"), patch(
            "cobo_cli.commands.node.prepare_home", return_value=home
        ):
            result = _invoke(["start", "--key-file", "/nonexistent"])
        assert result.exit_code != 0
        assert "cobo node init" in result.output

    def test_status_reports_relay_state_for_a_running_container(self, tmp_path):
        home = tmp_path / ".cobo" / "tss-node" / "prod"
        home.mkdir(parents=True)
        (home / "node_id").write_text(NODE_ID + "\n")
        state = {"State": {"Status": "running"}}
        with patch("cobo_cli.commands.node.node_home", return_value=home), patch(
            "cobo_cli.commands.node.container_state", return_value=state
        ), patch(
            "cobo_cli.commands.node.relay_state",
            return_value="connected to the relay",
        ):
            result = _invoke(["status"])
        assert result.exit_code == 0
        assert NODE_ID in result.output
        assert "connected to the relay" in result.output

    def test_stop_is_calm_when_nothing_runs(self):
        with patch("cobo_cli.commands.node.container_state", return_value=None):
            result = _invoke(["stop"])
        assert result.exit_code == 0
        assert "nothing to stop" in result.output


def test_mpc_session_traffic_counts_as_connected():
    # Right after a keygen the tail is all session logs; that traffic only
    # flows over a live relay connection, so it must not read as inactivity.
    logs = "KeyGen task completed in session abc:1-xyz, group info:\n" * 3
    completed = MagicMock(stdout=logs, stderr="")
    with patch("cobo_cli.utils.tss_node.subprocess.run", return_value=completed):
        assert "connected to the relay" in relay_state("prod")
