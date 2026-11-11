import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest
import requests
from click.testing import CliRunner

from cobo_cli.commands import delete_api, get_api, post_api
from cobo_cli.commands.doc import doc
from cobo_cli.commands.webhook import webhook
from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.utils.config import ConfigManager
from cobo_cli.utils.openapi import SPEC_HINT, load_api_spec

SPEC_YAML = b"openapi: 3.0.0\npaths: {}\n"
# cobo_cli.commands re-exports the ``webhook`` group under the module's own
# name, so a dotted patch target would resolve to the group, not the module.
webhook_module = sys.modules["cobo_cli.commands.webhook"]


@pytest.fixture
def cobo_home(tmp_path):
    """Point the spec cache at an empty directory instead of ~/.cobo."""
    with patch("cobo_cli.utils.openapi.get_config_path", return_value=str(tmp_path)):
        yield tmp_path


def _context(tmp_path, spec_url=None):
    config_manager = ConfigManager(config_file=str(tmp_path / "config.toml"))
    if spec_url:
        config_manager.set_config("spec_url", spec_url)
    return CommandContext(
        env=EnvironmentType.DEVELOPMENT,
        auth_method=AuthMethodType.APIKEY,
        config_manager=config_manager,
        api_spec=None,
    )


def _response(status_code=200, json_body=None, text="ok"):
    response = MagicMock(status_code=status_code, text=text)
    if json_body is None:
        response.json.side_effect = json.JSONDecodeError("no json", text, 0)
    else:
        response.json.return_value = json_body
    return response


class TestLoadApiSpec:
    def test_no_cache_and_no_url_returns_none_without_downloading(self, cobo_home):
        with patch("cobo_cli.utils.openapi.requests.get") as get:
            assert load_api_spec(spec_url=None) is None
            assert load_api_spec(spec_url="") is None
        get.assert_not_called()

    def test_stale_cache_is_used_when_refresh_fails(self, cobo_home):
        spec_file = cobo_home / "openapi.yaml"
        spec_file.write_bytes(SPEC_YAML)
        two_weeks_ago = time.time() - 14 * 24 * 60 * 60
        os.utime(spec_file, (two_weeks_ago, two_weeks_ago))

        with patch(
            "cobo_cli.utils.openapi.requests.get",
            side_effect=requests.ConnectionError("down"),
        ) as get:
            spec = load_api_spec(spec_url="https://example.com/spec.yaml")

        get.assert_called_once()
        assert spec == {"openapi": "3.0.0", "paths": {}}

    def test_downloads_and_caches_when_url_is_set(self, cobo_home):
        response = MagicMock(content=SPEC_YAML)
        with patch("cobo_cli.utils.openapi.requests.get", return_value=response) as get:
            spec = load_api_spec(spec_url="https://example.com/spec.yaml")

        assert get.call_args.args[0] == "https://example.com/spec.yaml"
        assert "timeout" in get.call_args.kwargs
        assert (cobo_home / "openapi.yaml").read_bytes() == SPEC_YAML
        assert spec == {"openapi": "3.0.0", "paths": {}}

    def test_unparseable_cache_returns_none(self, cobo_home):
        (cobo_home / "openapi.yaml").write_bytes(b"just a string")
        assert load_api_spec() is None


class TestApiCommandsWithoutSpec:
    def _invoke(self, command, args, tmp_path, response=None):
        response = response or _response(json_body={"ok": True})
        with patch(
            "cobo_cli.utils.api.make_request", return_value=response
        ) as make_request:
            result = CliRunner().invoke(command, args, obj=_context(tmp_path))
        return result, make_request

    def test_get_sends_pairs_as_query_params(self, cobo_home, tmp_path):
        result, make_request = self._invoke(
            get_api, ["/wallets", "--limit", "10"], tmp_path
        )
        assert result.exit_code == 0, result.output
        make_request.assert_called_once()
        assert make_request.call_args.args[1:] == ("GET", "/wallets")
        assert make_request.call_args.kwargs == {"params": {"limit": "10"}}
        assert '"ok": true' in result.output

    def test_delete_sends_pairs_as_query_params(self, cobo_home, tmp_path):
        _, make_request = self._invoke(
            delete_api, ["/wallets/w1", "--force", "1"], tmp_path
        )
        assert make_request.call_args.args[1:] == ("DELETE", "/wallets/w1")
        assert make_request.call_args.kwargs == {"params": {"force": "1"}}

    def test_post_parses_json_arrays_and_objects(self, cobo_home, tmp_path):
        result, make_request = self._invoke(
            post_api,
            ["/x", "--events", '["a"]', "--meta", '{"k": 1}', "--name", "n"],
            tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert make_request.call_args.args[1:] == ("POST", "/x")
        assert make_request.call_args.kwargs["json"] == {
            "events": ["a"],
            "meta": {"k": 1},
            "name": "n",
        }

    def test_post_keeps_json_scalars_as_typed_strings(self, cobo_home, tmp_path):
        _, make_request = self._invoke(
            post_api,
            [
                "/transactions/transfer",
                "--amount",
                "0.1",
                "--request_id",
                "123",
                "--flag",
                "true",
                "--note",
                "null",
                "--label",
                '"abc"',
            ],
            tmp_path,
        )
        assert make_request.call_args.kwargs["json"] == {
            "amount": "0.1",
            "request_id": "123",
            "flag": "true",
            "note": "null",
            "label": '"abc"',
        }

    def test_post_bare_trailing_flag_stays_true(self, cobo_home, tmp_path):
        _, make_request = self._invoke(post_api, ["/x", "--dry_run"], tmp_path)
        assert make_request.call_args.kwargs["json"] == {"dry_run": True}

    def test_post_without_pairs_sends_no_body(self, cobo_home, tmp_path):
        _, make_request = self._invoke(post_api, ["/x"], tmp_path)
        assert make_request.call_args.kwargs["json"] is None

    def test_non_json_response_is_printed_as_text(self, cobo_home, tmp_path):
        result, _ = self._invoke(
            get_api, ["/wallets"], tmp_path, response=_response(text="plain body")
        )
        assert "plain body" in result.output

    @pytest.mark.parametrize("flag", ["-l", "-d"])
    def test_list_and_describe_need_a_spec(self, cobo_home, tmp_path, flag):
        args = [flag] if flag == "-l" else [flag, "/wallets"]
        with patch("cobo_cli.utils.openapi.requests.get") as get:
            result, make_request = self._invoke(get_api, args, tmp_path)
        assert result.exit_code != 0
        assert SPEC_HINT in result.output
        get.assert_not_called()
        make_request.assert_not_called()


class TestDocWithoutSpec:
    def test_update_without_spec_url_shows_hint(self, cobo_home, tmp_path):
        with patch("cobo_cli.utils.openapi.requests.get") as get:
            result = CliRunner().invoke(doc, ["-u"], obj=_context(tmp_path))
        assert result.exit_code != 0
        assert SPEC_HINT in result.output
        get.assert_not_called()

    def test_update_downloads_from_configured_url(self, cobo_home, tmp_path):
        context = _context(tmp_path, spec_url="https://example.com/spec.yaml")
        with patch(
            "cobo_cli.utils.openapi.requests.get",
            return_value=MagicMock(content=SPEC_YAML),
        ):
            result = CliRunner().invoke(doc, ["-u"], obj=context)
        assert result.exit_code == 0, result.output
        assert "downloaded successfully" in result.output
        assert (cobo_home / "openapi.yaml").read_bytes() == SPEC_YAML

    def test_update_failure_is_an_error(self, cobo_home, tmp_path):
        context = _context(tmp_path, spec_url="https://example.com/spec.yaml")
        with patch(
            "cobo_cli.utils.openapi.requests.get",
            side_effect=requests.ConnectionError("down"),
        ):
            result = CliRunner().invoke(doc, ["-u"], obj=context)
        assert result.exit_code != 0
        assert "Failed to update" in result.output

    def test_api_path_without_spec_shows_hint(self, cobo_home, tmp_path):
        result = CliRunner().invoke(doc, ["/wallets"], obj=_context(tmp_path))
        assert result.exit_code != 0
        assert SPEC_HINT in result.output


DEFINITIONS = [
    {"event_type": "wallets.transaction.created", "description": "Created"},
    {"event_type": "wallets.transaction.updated"},
]


class TestWebhookEventTypes:
    def _invoke(self, args, tmp_path, definitions_response, trigger_response=None):
        def fake_request(ctx, method, path, **kwargs):
            if path == "/webhooks/event_definitions":
                return definitions_response
            return trigger_response

        with patch.object(
            webhook_module, "make_request", side_effect=fake_request
        ) as make_request:
            result = CliRunner().invoke(webhook, args, obj=_context(tmp_path))
        return result, make_request

    @pytest.mark.parametrize("body", [DEFINITIONS, {"data": DEFINITIONS}])
    def test_events_lists_types_from_the_server(self, tmp_path, body):
        result, make_request = self._invoke(
            ["events"], tmp_path, _response(json_body=body)
        )
        assert result.exit_code == 0, result.output
        assert make_request.call_args.args[1:] == (
            "GET",
            "/webhooks/event_definitions",
        )
        assert "- wallets.transaction.created: Created" in result.output
        assert "- wallets.transaction.updated" in result.output

    def test_events_fetch_failure_is_an_error(self, tmp_path):
        result, _ = self._invoke(
            ["events"], tmp_path, _response(status_code=404, text="not found")
        )
        assert result.exit_code != 0
        assert "404 not found" in result.output

    def test_trigger_posts_even_when_fetch_fails(self, tmp_path):
        result, make_request = self._invoke(
            ["trigger", "wallets.transaction.created"],
            tmp_path,
            _response(status_code=500, text="boom"),
            trigger_response=_response(status_code=201, json_body={"ok": True}),
        )
        assert result.exit_code == 0, result.output
        assert "Webhook event triggered successfully." in result.output
        last_call = make_request.call_args
        assert last_call.args[1:] == ("POST", "/webhooks/events/trigger")
        assert last_call.kwargs["json"] == {"event_type": "wallets.transaction.created"}

    def test_trigger_rejects_unknown_type_when_list_is_available(self, tmp_path):
        result, make_request = self._invoke(
            ["trigger", "no.such.event"],
            tmp_path,
            _response(json_body=DEFINITIONS),
        )
        assert result.exit_code != 0
        assert "cobo webhook events" in result.output
        assert make_request.call_count == 1

    def test_listen_without_events_needs_the_list(self, tmp_path):
        result, _ = self._invoke(
            ["listen"], tmp_path, _response(status_code=500, text="boom")
        )
        assert result.exit_code != 0
        assert "--events" in result.output
