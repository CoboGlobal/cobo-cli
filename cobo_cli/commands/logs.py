import json
import threading

import click
import websocket

from cobo_cli.data.context import CommandContext
from cobo_cli.utils.ws import generate_ws_apikey_auth_headers


@click.group("logs", help="Commands related to log operations.")
def logs():
    pass


@logs.command("tail", help="Tail the request logs from Cobo.")
@click.option("--http-method", type=str, help="Filter logs by HTTP method.")
@click.option("--request-path", type=str, help="Filter logs by request path.")
@click.option("--status-code", type=str, help="Filter logs by status code.")
@click.option("--api-key", type=str, help="Filter logs by API key.")
@click.option("--ip-address", type=str, help="Filter logs by IP address.")
@click.pass_context
def tail(
    ctx: click.Context,
    http_method: str,
    request_path: str,
    status_code: str,
    api_key: str,
    ip_address: str,
):
    """Tail the request logs from Cobo."""
    command_context: CommandContext = ctx.obj
    params = {
        "method": http_method,
        "api_endpoint": request_path,
        "status": status_code,
        "api_key": api_key,
        "ip_address": ip_address,
    }

    # Construct WebSocket URL
    base_url = command_context.config_manager.get_config("websocket_host")
    ws_endpoint = "/v2/api_logs/stream/"
    ws_url = f"{base_url}{ws_endpoint}"

    def on_message(ws, message):
        data = json.loads(message)
        api_log = data.get("message", {}).get("message", {})
        if api_log:
            try:
                print_log_detail(api_log)
            except Exception:
                pass

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
                    "action": "api_logs_fetch",
                    "message": params,
                }
            )
        )

    api_secret = command_context.config_manager.get_config("api_secret")
    headers = generate_ws_apikey_auth_headers(api_secret, ws_endpoint)
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        header=headers,
    )

    click.echo("Listening for api logs")
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()

    try:
        wst.join()
    except KeyboardInterrupt:
        click.echo("Stopping api log listener...")
        ws.close()


def print_log_detail(log_detail):
    click.echo("=" * 50)
    click.echo(click.style("API Log Details", fg="cyan", bold=True))
    click.echo("=" * 50)

    click.echo(
        click.style("Log ID:", fg="yellow") + f" {log_detail['api_request_uuid']}"
    )
    click.echo(click.style("Timestamp:", fg="yellow") + f" {log_detail['time']}")
    click.echo(click.style("Method:", fg="yellow") + f" {log_detail['api_method']}")
    click.echo(click.style("Endpoint:", fg="yellow") + f" {log_detail['api_endpoint']}")
    click.echo(click.style("Status Code:", fg="yellow") + f" {log_detail['status']}")
    click.echo(click.style("IP Address:", fg="yellow") + f" {log_detail['ip_address']}")
    click.echo(click.style("API Key:", fg="yellow") + f" {log_detail['api_key']}")

    click.echo("\n" + click.style("Query Parameters:", fg="green", bold=True))
    click.echo(json.dumps(json.loads(log_detail.get("query_params", "{}")), indent=2))

    click.echo("\n" + click.style("Request Body:", fg="green", bold=True))
    click.echo(json.dumps(json.loads(log_detail.get("request_body", "{}")), indent=2))

    click.echo("\n" + click.style("Response Body:", fg="green", bold=True))
    click.echo(json.dumps(json.loads(log_detail["response_body"]), indent=2))

    click.echo("=" * 50)


if __name__ == "__main__":
    logs()
