import copy
import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from cobo_cli.commands.webhook import webhook
from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.utils.config import ConfigManager
from cobo_cli.utils.webhook_samples import build_event
from cobo_cli.utils.webhook_signing import (
    COBO_PUBLIC_KEYS,
    TEST_PUBLIC_KEY,
    build_headers,
)

ENDPOINT = "http://localhost:8000/webhooks/cobo"


def verify_like_documented_handler(raw_body: bytes, headers: dict) -> bool:
    """Reproduce the verification steps published for webhook endpoints."""
    timestamp = headers.get("BIZ_TIMESTAMP") or headers.get("BIZ-TIMESTAMP")
    signature = headers.get("BIZ_RESP_SIGNATURE") or headers.get("BIZ-RESP-SIGNATURE")
    digest = hashlib.sha256(
        hashlib.sha256(raw_body + b"|" + timestamp.encode()).digest()
    ).digest()
    try:
        VerifyKey(bytes.fromhex(TEST_PUBLIC_KEY)).verify(
            digest, bytes.fromhex(signature)
        )
        return True
    except BadSignatureError:
        return False


class TestSignedSampleVerifies:
    def test_a_documented_handler_accepts_the_signed_body(self):
        event = build_event(
            "deposit", "wallets.transaction.updated", "Completed", ENDPOINT
        )
        raw_body = json.dumps(event, separators=(",", ":")).encode()
        headers, _ = build_headers(raw_body, "1787022807609")

        assert verify_like_documented_handler(raw_body, headers) is True

    def test_modifying_one_byte_breaks_verification(self):
        event = build_event(
            "deposit", "wallets.transaction.updated", "Completed", ENDPOINT
        )
        raw_body = json.dumps(event, separators=(",", ":")).encode()
        headers, _ = build_headers(raw_body, "1787022807609")

        tampered = raw_body.replace(b'"amount":"0.0002"', b'"amount":"9.9999"', 1)
        assert tampered != raw_body
        assert verify_like_documented_handler(tampered, headers) is False

    def test_both_header_spellings_are_sent(self):
        headers, signature = build_headers(b"{}", "1")
        for name in ("BIZ_TIMESTAMP", "BIZ-TIMESTAMP"):
            assert headers[name] == "1"
        for name in ("BIZ_RESP_SIGNATURE", "BIZ-RESP-SIGNATURE"):
            assert headers[name] == signature


class TestSamplePayloadShapes:
    """Deposits and withdrawals carry the recipient in different places; a
    handler written against only one shape silently drops the other."""

    def test_deposit_carries_recipient_directly_under_destination(self):
        data = build_event(
            "deposit", "wallets.transaction.updated", "Completed", ENDPOINT
        )["data"]
        assert data["destination"]["destination_type"] == "DepositToAddress"
        assert data["destination"]["address"]
        assert data["destination"]["amount"]

    def test_withdrawal_nests_recipient_under_account_output(self):
        data = build_event(
            "withdrawal", "wallets.transaction.updated", "Completed", ENDPOINT
        )["data"]
        assert data["destination"]["destination_type"] == "Address"
        assert data["destination"]["account_output"]["address"]
        assert data["destination"]["account_output"]["amount"]

    @pytest.mark.parametrize("sample_type", ["deposit", "withdrawal"])
    def test_neither_shape_has_a_top_level_address_or_amount(self, sample_type):
        data = build_event(
            sample_type, "wallets.transaction.updated", "Completed", ENDPOINT
        )["data"]
        assert "address" not in data
        assert "amount" not in data

    def test_envelope_matches_published_schema(self):
        event = build_event(
            "deposit", "wallets.transaction.created", "Submitted", ENDPOINT
        )
        assert set(event) == {"event_id", "url", "created_timestamp", "type", "data"}
        assert event["type"] == "wallets.transaction.created"
        assert event["data"]["status"] == "Submitted"
        assert event["data"]["data_type"] == "Transaction"


def _context():
    """The context the root command builds before any subcommand runs."""
    config_manager = ConfigManager()
    return CommandContext(
        env=EnvironmentType(config_manager.get_config("environment")),
        auth_method=AuthMethodType.APIKEY,
        config_manager=config_manager,
        api_spec=None,
    )


def _invoke(args, status_code, body="ok"):
    response = MagicMock(status_code=status_code, text=body)
    with patch(
        "cobo_cli.commands.webhook.requests.post", return_value=response
    ) as post:
        result = CliRunner().invoke(
            webhook, ["test", "--forward", ENDPOINT] + args, obj=_context()
        )
    return result, post


class TestCommandVerdict:
    def test_signs_exactly_the_bytes_it_sends(self):
        _, post = _invoke([], 200)
        sent_body = post.call_args.kwargs["data"]
        sent_headers = post.call_args.kwargs["headers"]
        assert verify_like_documented_handler(sent_body, sent_headers) is True

    def test_accepts_when_endpoint_returns_2xx(self):
        result, _ = _invoke([], 200)
        assert result.exit_code == 0
        assert "Accepted" in result.output

    def test_fails_when_endpoint_does_not_return_2xx(self):
        result, _ = _invoke([], 500)
        assert result.exit_code != 0
        assert "did not return 200 or 201" in result.output

    def test_tamper_mode_sends_a_body_that_no_longer_verifies(self):
        _, post = _invoke(["--tamper"], 401)
        sent_body = post.call_args.kwargs["data"]
        sent_headers = post.call_args.kwargs["headers"]
        assert verify_like_documented_handler(sent_body, sent_headers) is False

    def test_tamper_mode_fails_when_endpoint_wrongly_accepts(self):
        result, _ = _invoke(["--tamper"], 200)
        assert result.exit_code != 0
        assert "signature does not match" in result.output

    def test_tamper_mode_passes_when_endpoint_rejects(self):
        result, _ = _invoke(["--tamper"], 401)
        assert result.exit_code == 0
        assert "Correctly rejected" in result.output


def test_injected_values_land_in_the_deposit_slot():
    event = build_event(
        "deposit",
        "wallets.transaction.updated",
        "Completed",
        "http://x",
        wallet_id="my-wallet",
        address="0xmine",
        amount="12.5",
    )
    data = event["data"]
    assert data["wallet_id"] == "my-wallet"
    assert data["destination"]["wallet_id"] == "my-wallet"
    assert data["destination"]["address"] == "0xmine"
    assert data["destination"]["amount"] == "12.5"


def test_injected_values_land_in_the_withdrawal_slot():
    event = build_event(
        "withdrawal",
        "wallets.transaction.updated",
        "Completed",
        "http://x",
        wallet_id="my-wallet",
        address="0xmine",
        amount="12.5",
    )
    data = event["data"]
    # The owned side of a withdrawal is the source, and the recipient sits one
    # level deeper than it does for a deposit.
    assert data["wallet_id"] == "my-wallet"
    assert data["source"]["wallet_id"] == "my-wallet"
    assert data["destination"]["account_output"]["address"] == "0xmine"
    assert data["destination"]["account_output"]["amount"] == "12.5"
    assert "address" not in data["destination"]


@pytest.mark.parametrize("sample_type", ["deposit", "withdrawal"])
def test_tamper_flips_the_status_whatever_the_shape(sample_type):
    # Status is the one field every transaction carries regardless of shape,
    # and flipping it is the change that actually pays off for an attacker: a
    # handler that credits on Completed without verifying can be told anything
    # completed.
    _, post = _invoke(["--type", sample_type, "--status", "Failed", "--tamper"], 400)
    sent_body = post.call_args.kwargs["data"]
    sent_headers = post.call_args.kwargs["headers"]
    assert json.loads(sent_body)["data"]["status"] == "Completed"
    assert verify_like_documented_handler(sent_body, sent_headers) is False


REAL_TRANSACTION = {
    "transaction_id": "tx-from-the-api",
    "wallet_id": "wallet-from-the-api",
    "type": "Withdrawal",
    "status": "Failed",
    "destination": {"account_output": {"address": "0xreal", "amount": "3.25"}},
}


def _invoke_fetching(args, transactions, list_status=200, post_status=200):
    listing = MagicMock(status_code=list_status)
    # A fresh copy per call: the command edits the fetched record in place for
    # --tamper, which on real data is a throwaway parse but here would leak
    # into the next test through the shared literal.
    listing.json.return_value = {"data": copy.deepcopy(transactions)}
    response = MagicMock(status_code=post_status, text="ok")
    with patch(
        "cobo_cli.commands.webhook.make_request", return_value=listing
    ) as fetch, patch(
        "cobo_cli.commands.webhook.requests.post", return_value=response
    ) as post:
        result = CliRunner().invoke(
            webhook, ["test", "--forward", ENDPOINT] + args, obj=_context()
        )
    return result, fetch, post


class TestRealTransactionSource:
    def test_sends_the_fetched_record_plus_the_delivery_discriminator(self):
        _, _, post = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api"], [REAL_TRANSACTION]
        )
        sent = json.loads(post.call_args.kwargs["data"])
        # Every field of the record reaches the handler unchanged, and the one
        # field a delivery adds over the REST representation is `data_type`.
        assert sent["data"] == {**REAL_TRANSACTION, "data_type": "Transaction"}
        assert set(sent) == {"event_id", "url", "created_timestamp", "type", "data"}

    def test_fetched_payload_is_signed_like_any_other(self):
        _, _, post = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api"], [REAL_TRANSACTION]
        )
        assert (
            verify_like_documented_handler(
                post.call_args.kwargs["data"], post.call_args.kwargs["headers"]
            )
            is True
        )

    def test_queries_the_list_endpoint_not_the_detail_one(self):
        # The detail endpoint carries a `timeline` that no delivery has.
        _, fetch, _ = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api"], [REAL_TRANSACTION]
        )
        assert fetch.call_args.args[1:] == ("GET", "/transactions")
        assert fetch.call_args.kwargs["params"]["transaction_ids"] == "tx-from-the-api"

    def test_wallet_source_asks_for_the_latest_transaction(self):
        _, fetch, _ = _invoke_fetching(["--from-wallet", "w-1"], [REAL_TRANSACTION])
        assert fetch.call_args.kwargs["params"] == {"limit": 1, "wallet_ids": "w-1"}

    def test_tamper_works_on_a_fetched_transaction(self):
        _, _, post = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api", "--tamper"],
            [REAL_TRANSACTION],
            post_status=401,
        )
        sent_body = post.call_args.kwargs["data"]
        assert json.loads(sent_body)["data"]["status"] == "Completed"
        assert (
            verify_like_documented_handler(sent_body, post.call_args.kwargs["headers"])
            is False
        )

    def test_reports_when_no_transaction_matches(self):
        result, _, post = _invoke_fetching(["--from-wallet", "w-1"], [])
        assert result.exit_code != 0
        assert "Found no transaction" in result.output
        post.assert_not_called()

    def test_rejects_both_sources_at_once(self):
        result, fetch, _ = _invoke_fetching(
            ["--from-transaction", "t", "--from-wallet", "w"], [REAL_TRANSACTION]
        )
        assert result.exit_code != 0
        assert "not both" in result.output
        fetch.assert_not_called()


class TestReportedSource:
    def test_reports_the_fetched_transaction_not_the_sample_defaults(self):
        # --type/--status shape the samples only; echoing them for a fetched
        # transaction reported a withdrawal as a deposit.
        result, _, _ = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api"], [REAL_TRANSACTION]
        )
        assert "your transaction tx-from-the-api [Withdrawal, Failed]" in result.output
        assert "deposit" not in result.output

    def test_reports_a_sample_as_a_sample(self):
        result, _ = _invoke(["--type", "withdrawal"], 200)
        assert "a sample payload [withdrawal, Completed]" in result.output


class TestLiveKeyGuidance:
    def test_names_the_key_for_the_configured_environment(self):
        result, _ = _invoke([], 200)
        # Whichever environment the runner is configured for, the key printed
        # must be that environment's -- naming the other one is the mistake
        # this output exists to prevent.
        printed = [k for k in COBO_PUBLIC_KEYS.values() if k in result.output]
        assert len(printed) == 1
        environment = next(e for e, k in COBO_PUBLIC_KEYS.items() if k == printed[0])
        assert f"Cobo's {environment} key" in result.output

    def test_still_marks_the_signing_key_as_the_test_one(self):
        result, _ = _invoke([], 200)
        assert TEST_PUBLIC_KEY in result.output
        assert TEST_PUBLIC_KEY not in COBO_PUBLIC_KEYS.values()


def test_env_override_selects_the_key_it_names():
    # --env changes which section the CLI works against, but the persisted
    # `environment` setting stays put, so reading it named the wrong key.
    runner = CliRunner()
    with patch(
        "cobo_cli.commands.webhook.requests.post",
        return_value=MagicMock(status_code=200, text="ok"),
    ):
        outputs = {}
        for environment in COBO_PUBLIC_KEYS:
            context = _context()
            context.env = EnvironmentType(environment)
            outputs[environment] = runner.invoke(
                webhook, ["test", "--forward", ENDPOINT], obj=context
            ).output
    for environment, key in COBO_PUBLIC_KEYS.items():
        assert key in outputs[environment]
        for other, other_key in COBO_PUBLIC_KEYS.items():
            if other != environment:
                assert other_key not in outputs[environment]


@pytest.mark.parametrize("sample_type", ["deposit", "withdrawal"])
def test_sample_carries_the_event_data_discriminator(sample_type):
    event = build_event(
        sample_type, "wallets.transaction.updated", "Completed", "http://x"
    )
    assert event["data"]["data_type"] == "Transaction"


def test_fetched_transaction_gains_the_event_data_discriminator():
    # `data_type` is absent from the REST representation and present on a
    # delivery; the published schema dispatches on it, so sending a fetched
    # transaction without it would fail a handler that deserialises the event
    # with a generated model -- while real deliveries parse fine.
    fetched = dict(REAL_TRANSACTION)
    assert "data_type" not in fetched
    _, _, post = _invoke_fetching(["--from-transaction", "tx-from-the-api"], [fetched])
    sent = json.loads(post.call_args.kwargs["data"])
    assert sent["data"]["data_type"] == "Transaction"
