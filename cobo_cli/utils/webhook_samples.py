"""Sample webhook payloads used by `cobo webhook test`.

The shapes below are taken from real WaaS 2.0 transactions. The single most
common integration mistake is assuming a deposit and a withdrawal carry the
recipient in the same place — they do not:

    deposit     -> destination.address / destination.amount
    withdrawal  -> destination.account_output.address / .amount

Neither carries a top-level ``address`` or ``amount``. A handler written
against only one of the two shapes silently drops the other.
"""

import time
import uuid
from typing import Dict, Optional

# The envelope follows the WebhookEvent schema published in the OpenAPI spec:
# event_id / url / created_timestamp / type / data.
WEBHOOK_EVENT_TYPES = [
    "wallets.transaction.created",
    "wallets.transaction.updated",
    "wallets.transaction.succeeded",
    "wallets.transaction.failed",
]

SAMPLE_TYPES = ("deposit", "withdrawal")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _deposit_transaction(status: str) -> Dict:
    return {
        "transaction_id": str(uuid.uuid4()),
        "cobo_id": "20200101000000000000000000000001",
        "wallet_id": "11111111-1111-4111-8111-111111111111",
        "type": "Deposit",
        "status": status,
        "chain_id": "SETH",
        "token_id": "SETH",
        "source": {
            "source_type": "DepositFromAddress",
            "addresses": ["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        },
        # Recipient lives directly under `destination` for deposits.
        "destination": {
            "destination_type": "DepositToAddress",
            "wallet_id": "11111111-1111-4111-8111-111111111111",
            "wallet_type": "MPC",
            "wallet_subtype": "Org-Controlled",
            "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "amount": "0.0002",
        },
        "initiator_type": "External",
        "confirmed_num": 64,
        "confirming_threshold": 64,
        "transaction_hash": "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        "block_info": {
            "block_number": 11512393,
            "block_timestamp": 1787022804000,
        },
        "created_timestamp": 1787022807609,
        "updated_timestamp": _now_ms(),
        "data_type": "Transaction",
    }


def _withdrawal_transaction(status: str) -> Dict:
    return {
        "transaction_id": str(uuid.uuid4()),
        "cobo_id": "20200101000000000000000000000002",
        "request_id": "your-idempotency-key",
        "wallet_id": "22222222-2222-4222-8222-222222222222",
        "type": "Withdrawal",
        "status": status,
        "chain_id": "SETH",
        "token_id": "SETH",
        "source": {
            "source_type": "Org-Controlled",
            "wallet_id": "22222222-2222-4222-8222-222222222222",
            "address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        },
        # Recipient is nested under `account_output` for withdrawals.
        "destination": {
            "destination_type": "Address",
            "account_output": {
                "address": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "amount": "0.0002",
            },
            "force_internal": False,
            "force_external": False,
        },
        "fee": {
            "fee_type": "EVM_Legacy",
            "token_id": "SETH",
            "gas_price": "1059608303",
            "gas_limit": "21000",
            "fee_used": "0.000022251774363",
        },
        "initiator_type": "API",
        "confirmed_num": 64,
        "confirming_threshold": 64,
        "transaction_hash": "0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        "created_timestamp": 1787022786000,
        "updated_timestamp": _now_ms(),
        "data_type": "Transaction",
    }


def recipient_slot(data: Dict) -> Dict:
    """Return the dict that holds the recipient ``address`` and ``amount``.

    This is the shape difference the module docstring warns about, resolved in
    one place: a deposit keeps the recipient directly under ``destination``, a
    withdrawal nests it one level deeper under ``account_output``.
    """
    destination = data["destination"]
    return destination.get("account_output", destination)


def build_event(
    sample_type: str,
    event_type: str,
    status: str,
    url: str,
    wallet_id: Optional[str] = None,
    address: Optional[str] = None,
    amount: Optional[str] = None,
) -> Dict:
    """Build a complete webhook event envelope around a sample transaction.

    The sample identifiers are deliberately synthetic: no hardcoded value can
    mean anything in someone else's database. Pass ``wallet_id`` / ``address``
    / ``amount`` to make the event match a record the handler under test can
    actually look up. Each is written to the slot the chosen shape uses, so a
    caller never has to know which of the two layouts applies.
    """
    if sample_type not in SAMPLE_TYPES:
        raise ValueError(f"sample_type must be one of {SAMPLE_TYPES}")
    data = (
        _deposit_transaction(status)
        if sample_type == "deposit"
        else _withdrawal_transaction(status)
    )
    if wallet_id is not None:
        # The wallet appears both at the top level and on the side of the
        # transfer this org owns: the destination for a deposit, the source
        # for a withdrawal.
        data["wallet_id"] = wallet_id
        owned = data["destination"] if sample_type == "deposit" else data["source"]
        owned["wallet_id"] = wallet_id
    slot = recipient_slot(data)
    if address is not None:
        slot["address"] = address
    if amount is not None:
        slot["amount"] = amount
    return {
        "event_id": str(uuid.uuid4()),
        "url": url,
        "created_timestamp": _now_ms(),
        "type": event_type,
        "data": data,
    }
