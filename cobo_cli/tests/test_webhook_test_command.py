import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from cobo_cli.commands.webhook import webhook
from cobo_cli.utils.webhook_samples import build_event
from cobo_cli.utils.webhook_signing import TEST_PUBLIC_KEY, build_headers

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
    """充值与提现把收款方放在不同位置, 只按其中一种写的 handler 会静默漏掉另一种。"""

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


def _invoke(args, status_code, body="ok"):
    response = MagicMock(status_code=status_code, text=body)
    with patch(
        "cobo_cli.commands.webhook.requests.post", return_value=response
    ) as post:
        result = CliRunner().invoke(webhook, ["test", "--forward", ENDPOINT] + args)
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
    listing.json.return_value = {"data": transactions}
    response = MagicMock(status_code=post_status, text="ok")
    with patch(
        "cobo_cli.commands.webhook.make_request", return_value=listing
    ) as fetch, patch(
        "cobo_cli.commands.webhook.requests.post", return_value=response
    ) as post:
        result = CliRunner().invoke(webhook, ["test", "--forward", ENDPOINT] + args)
    return result, fetch, post


class TestRealTransactionSource:
    def test_sends_the_fetched_transaction_untouched(self):
        _, _, post = _invoke_fetching(
            ["--from-transaction", "tx-from-the-api"], [REAL_TRANSACTION]
        )
        sent = json.loads(post.call_args.kwargs["data"])
        # Nothing added, nothing dropped: the list record is the webhook data.
        assert sent["data"] == REAL_TRANSACTION
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
