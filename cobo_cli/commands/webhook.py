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
)
from cobo_cli.utils.webhook_signing import TEST_PUBLIC_KEY, build_headers
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
    "--tamper",
    is_flag=True,
    help="Corrupt the body after signing. A correct endpoint must reject this.",
)
def test_webhook(forward, sample_type, event_type, status, tamper):
    """Verify a webhook handler without deploying it or waiting for a real event.

    The event is built and signed locally, so this works in every environment
    and needs no public URL. It is signed with a dedicated test key -- point
    your verifier at the key printed below while testing.
    """
    event = build_event(sample_type, event_type, status, forward)

    # Sign the exact bytes that go on the wire. Serialising once and reusing the
    # result is the whole point: re-encoding would change key order and break
    # the signature, which is the most common cause of "my verification fails".
    raw_body = json.dumps(event, separators=(",", ":")).encode()
    timestamp = str(int(time.time() * 1000))
    headers, signature = build_headers(raw_body, timestamp)

    if tamper:
        # Flip one byte after signing so the signature no longer matches.
        raw_body = raw_body.replace(b'"amount":"0.0002"', b'"amount":"9.9999"', 1)

    click.echo(f"Verification public key: {TEST_PUBLIC_KEY}")
    click.echo("  (test key -- switch back to your environment key before going live)")
    click.echo(f"Sending {event_type} [{sample_type}, {status}] to {forward}")
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
