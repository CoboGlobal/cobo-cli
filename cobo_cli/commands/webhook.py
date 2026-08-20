import json
import threading
import time

import click
import requests
import websocket

from cobo_cli.data.context import CommandContext
from cobo_cli.utils.api import load_api_spec, make_request
from cobo_cli.utils.webhook_samples import (
    SAMPLE_TYPES,
    WEBHOOK_EVENT_TYPES,
    build_event,
    wrap_event,
)
from cobo_cli.utils.webhook_signing import (
    COBO_PUBLIC_KEYS,
    TEST_PUBLIC_KEY,
    build_headers,
)
from cobo_cli.utils.ws import generate_ws_apikey_auth_headers


@click.group("webhook", help="Commands related to webhook operations.")
def webhook():
    pass


def get_valid_event_types(spec):
    webhook_event_schema = spec["components"]["schemas"]["WebhookEventType"]
    return webhook_event_schema["enum"]


class LazyChoice(click.Choice):
    def __init__(self, choices_func):
        self.choices_func = choices_func
        super().__init__([])

    def get_metavar(self, param):
        return "EVENT_TYPE"

    def get_missing_message(self, param):
        return "Use 'cobo webhook events' to see available event types."

    def convert(self, value, param, ctx):
        self.choices = self.choices_func(ctx)
        return super().convert(value, param, ctx)


def get_event_types(ctx):
    command_context: CommandContext = ctx.obj
    spec = command_context.api_spec or load_api_spec()
    return get_valid_event_types(spec)


@webhook.command("trigger", help="Manually trigger a webhook event.")
@click.argument("event_type", type=LazyChoice(get_event_types))
@click.option("--override", help="JSON string to override event data.")
@click.pass_context
def trigger(ctx, event_type, override):
    command_context: CommandContext = ctx.obj
    command_context.api_spec or load_api_spec()

    payload = {"event_type": event_type}

    if override:
        try:
            override_data = json.loads(override)
            if type(override_data) in [int, str, float, bool]:
                raise json.JSONDecodeError
            payload["override_data"] = override_data
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in override data.")
            return

    response = make_request(ctx, "POST", "/webhooks/events/trigger", json=payload)

    if response.status_code == 201:
        click.echo("Webhook event triggered successfully.")
        click.echo(json.dumps(response.json(), indent=2))
    else:
        click.echo(
            f"Failed to trigger webhook event. Status code: {response.status_code}"
        )
        click.echo(response.text)


@webhook.command("events", help="List all available webhook event types.")
@click.pass_context
def list_events(ctx):
    command_context: CommandContext = ctx.obj
    spec = command_context.api_spec or load_api_spec()
    event_types = get_valid_event_types(spec)
    click.echo("Available webhook event types:")
    for event_type in event_types:
        click.echo(f"- {event_type}")


@webhook.command("listen", help="Listen for webhook events using WebSocket.")
@click.option("--events", help="Comma-separated list of event types to listen for.")
@click.option("--forward", help="URL to forward events to.")
@click.pass_context
def listen(ctx, events, forward):
    command_context: CommandContext = ctx.obj
    spec = command_context.api_spec or load_api_spec()

    # Validate event types
    valid_event_types = get_valid_event_types(spec)
    if events:
        event_list = [e.strip() for e in events.split(",")]
        invalid_events = set(event_list) - set(valid_event_types)
        if invalid_events:
            click.echo(f"Error: Invalid event types: {', '.join(invalid_events)}")
            return
    else:
        event_list = valid_event_types

    # Construct WebSocket URL
    base_url = command_context.config_manager.get_config("websocket_host")
    ws_url = f"{base_url}/v2/webhooks/events/stream/"

    def on_message(ws, message):
        event = json.loads(message)
        event_data = event.get("message", {}).get("message", {})
        if not event_data:
            event_data = event
        click.echo(json.dumps(event_data, indent=2))
        if forward:
            try:
                requests.post(forward, json=event_data)
            except requests.RequestException as e:
                click.echo(f"Error forwarding event: {str(e)}")

    def on_error(ws, error):
        click.echo(f"WebSocket error: {str(error)}")

    def on_close(ws, close_status_code, close_msg):
        click.echo("WebSocket connection closed")

    def on_open(ws):
        click.echo("WebSocket connection established")
        ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "action": "webhook_event_fetch",
                    "message": {"event_type": event_list},
                }
            )
        )

    api_secret = command_context.config_manager.get_config("api_secret")
    headers = generate_ws_apikey_auth_headers(api_secret, "/v2/webhooks/events/stream/")
    # websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        header=headers,
    )

    click.echo(f"Listening for events: {', '.join(event_list)}")
    if forward:
        click.echo(f"Forwarding events to: {forward}")

    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    try:
        wst.join()
    except KeyboardInterrupt:
        click.echo("Stopping webhook listener...")
        ws.close()


if __name__ == "__main__":
    webhook()


def _fetch_transaction(ctx, transaction_id, wallet_id):
    """Read one of the caller's transactions in the shape a webhook carries.

    The list endpoint is used even when the transaction id is known. The
    service builds its webhook payload from that same list-shaped record,
    while the detail endpoint adds a ``timeline`` no delivery ever carries --
    so this needs nothing stripped and nothing filled in.
    """
    params = {"limit": 1}
    if transaction_id:
        params["transaction_ids"] = transaction_id
        described = f"transaction {transaction_id}"
    else:
        params["wallet_ids"] = wallet_id
        described = f"the most recent transaction of wallet {wallet_id}"

    response = make_request(ctx, "GET", "/transactions", params=params)
    if response.status_code != 200:
        raise click.ClickException(
            f"Could not read {described}: "
            f"{response.status_code} {response.text[:200]}"
        )
    transactions = response.json().get("data") or []
    if not transactions:
        raise click.ClickException(
            f"Found no transaction for {described}. Make one first, or drop "
            "--from-transaction/--from-wallet to send a sample payload."
        )
    return transactions[0]


@webhook.command(
    "test",
    help="Send a locally signed sample webhook event to your endpoint.",
)
@click.option(
    "--forward",
    required=True,
    help="Your webhook endpoint, e.g. http://localhost:8000/webhooks/cobo",
)
@click.option(
    "--type",
    "sample_type",
    type=click.Choice(SAMPLE_TYPES),
    default="deposit",
    show_default=True,
    help="Payload shape to send. Deposits and withdrawals carry the recipient "
    "in different places, so test both.",
)
@click.option(
    "--event",
    "event_type",
    type=click.Choice(WEBHOOK_EVENT_TYPES),
    default="wallets.transaction.updated",
    show_default=True,
    help="Event type placed in the envelope.",
)
@click.option(
    "--status",
    default="Completed",
    show_default=True,
    help="Transaction status carried in the event data.",
)
@click.option(
    "--from-transaction",
    "from_transaction",
    default=None,
    help="Build the event from one of your real transactions, fetched by id. "
    "The service builds its payload from the same record, so nothing is "
    "simulated except the envelope.",
)
@click.option(
    "--from-wallet",
    "from_wallet",
    default=None,
    help="Build the event from the most recent transaction of this wallet.",
)
@click.option(
    "--wallet-id",
    default=None,
    help="Sample payloads only: use your own wallet id so the handler can look "
    "the record up.",
)
@click.option(
    "--address",
    default=None,
    help="Use your own recipient address. Placed in whichever slot the chosen "
    "shape uses, so you need not know the layout.",
)
@click.option(
    "--amount",
    default=None,
    help="Use your own recipient amount, placed alongside --address.",
)
@click.option(
    "--tamper",
    is_flag=True,
    help="Corrupt the body after signing. A correct endpoint must reject this.",
)
@click.pass_context
def test_webhook(
    ctx,
    forward,
    sample_type,
    event_type,
    status,
    from_transaction,
    from_wallet,
    wallet_id,
    address,
    amount,
    tamper,
):
    """Verify a webhook handler without deploying it or waiting for a real event.

    Prefer --from-transaction or --from-wallet: the transaction is read from
    your own account in the same shape the service builds its payload from, so
    the only simulated part is the envelope, and your handler sees the chain,
    token, fee and status it will really see. Without them a sample payload is
    sent instead, which is what you need before any transaction exists.

    The event is signed locally, so this works in every environment and needs
    no public URL. It is signed with a dedicated test key -- point your
    verifier at the key printed below while testing.
    """
    if from_transaction and from_wallet:
        raise click.ClickException(
            "Pass either --from-transaction or --from-wallet, not both."
        )
    if from_transaction or from_wallet:
        data = _fetch_transaction(ctx, from_transaction, from_wallet)
        # Describe what is actually being sent. --type and --status shape the
        # samples only, and repeating them here would misreport a fetched
        # transaction as whatever the sample defaults happen to be.
        described = (
            f"your transaction {data.get('transaction_id')} "
            f"[{data.get('type')}, {data.get('status')}]"
        )
        event = wrap_event(data, event_type, forward)
    else:
        event = build_event(
            sample_type,
            event_type,
            status,
            forward,
            wallet_id=wallet_id,
            address=address,
            amount=amount,
        )
        described = f"a sample payload [{sample_type}, {status}]"

    # Sign the exact bytes that go on the wire. Serialising once and reusing the
    # result is the whole point: re-encoding would change key order and break
    # the signature, which is the most common cause of "my verification fails".
    raw_body = json.dumps(event, separators=(",", ":")).encode()
    timestamp = str(int(time.time() * 1000))
    headers, signature = build_headers(raw_body, timestamp)

    if tamper:
        # Flip the status, which every transaction carries whatever its shape,
        # and which is the change an attacker would actually want to make: a
        # handler that credits on Completed without checking the signature can
        # be told anything is Completed. Editing the parsed event and
        # re-dumping keeps key order, so the body stays valid JSON and is
        # guaranteed to differ from what was signed.
        data = event["data"]
        data["status"] = "Completed" if data.get("status") != "Completed" else "Failed"
        raw_body = json.dumps(event, separators=(",", ":")).encode()

    click.echo(f"Verification public key: {TEST_PUBLIC_KEY}")
    click.echo("  (test key -- point your verifier at it while testing)")
    # Name the key to go live with, and name the environment it belongs to.
    # Both of Cobo's keys verify signatures perfectly well; picking the wrong
    # one is what rejects every real delivery, and nothing local catches it.
    # ctx.obj.env, not config_manager.get_config("environment"): the latter
    # reports the persisted setting, so `--env prod` would still name the dev
    # key -- the very mix-up this output exists to prevent.
    environment = ctx.obj.env.value
    live_key = COBO_PUBLIC_KEYS.get(environment)
    if live_key:
        click.echo(f"  before going live, switch to Cobo's {environment} key:")
        click.echo(f"  {live_key}")
    else:
        click.echo(
            f"  before going live, switch to Cobo's key for the {environment} "
            "environment (see Set up a callback or webhook endpoint)"
        )
    click.echo(f"Sending {event_type} from {described} to {forward}")
    if tamper:
        click.echo("Body was modified after signing; your endpoint must reject it.")

    try:
        response = requests.post(forward, data=raw_body, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise click.ClickException(f"Could not reach {forward}: {e}")

    click.echo(f"Endpoint responded {response.status_code}: {response.text[:200]}")

    accepted = response.status_code in (200, 201)
    if tamper:
        if accepted:
            raise click.ClickException(
                "Endpoint accepted a payload whose signature does not match. "
                "Verify the signature against the raw request bytes before "
                "processing the event."
            )
        click.echo("Correctly rejected the tampered payload.")
        return

    if not accepted:
        raise click.ClickException(
            "Endpoint did not return 200 or 201. Cobo retries such deliveries up "
            "to 10 times and then marks the event Failed. Check that the "
            "signature is verified against the raw bytes and that the handler "
            "responds within 2 seconds."
        )
    click.echo(
        "Accepted. Now re-run with --tamper to confirm bad signatures are rejected."
    )
