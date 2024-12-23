import json
import logging
import time
import uuid
from typing import Union
from urllib.parse import parse_qs, urlparse

import click

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.utils.api import make_request

logger = logging.getLogger(__name__)


def is_response_success(body: Union[str, dict], stdout: bool = False) -> bool:
    if isinstance(body, str):
        body = json.loads(body)

    is_success = body.get("success", False)
    if not is_success and stdout:
        click.echo(
            f"Error creating auth. "
            f"error_code={body.get('error_code')}, "
            f"error_message={body.get('error_message')}, "
            f"error_id={body.get('error_id')}",
            err=True,
            color=True,
        )
    return is_success


def initiate_auth(
    ctx: click.Context, client_id: str, grant_dimension: str = None
) -> dict:
    logger.debug(
        f"initiate_auth called with client_id={client_id}, grant_dimension={grant_dimension}"
    )

    params = {
        "client_id": client_id,
        "response_type": "code",
        "state": str(uuid.uuid4()),
    }
    if grant_dimension:
        params["grant_dimension"] = grant_dimension

    api_path = "/oauth/authorize/initiate_auth"

    response = make_request(
        ctx, "POST", api_path, json=params, auth=AuthMethodType.NONE
    )
    return response.json()


def get_token(
    ctx: click.Context,
    token_url: str,
    auth_method: AuthMethodType = AuthMethodType.NONE,
) -> dict:
    logger.debug(f"get_token called with token_url={token_url}")

    parsed_url = urlparse(token_url)
    params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
    api_path = parsed_url.path

    response = make_request(
        ctx, "GET", api_path, prefix="", auth=auth_method, params=params
    )
    logger.debug(f"get_token, response: {response.text}")
    return response.json()


def poll_for_token(
    ctx: click.Context,
    token_url: str,
    auth_method: AuthMethodType,
    max_attempts: int = 180,
) -> dict:
    click.echo("Polling the token URL for the granted token...")
    for _ in range(max_attempts):
        body = get_token(ctx, token_url, auth_method)
        access_token = body.get("access_token")
        if access_token:
            return body
        abort = body.get("abort", False)
        if abort:
            click.echo("Authorization is rejected. Aborted.")
            return {}
        time.sleep(1)
    click.echo("Authorization failed, please retry.")
    return {}


def handle_browser_interaction(browser_url: str) -> None:
    click.echo(f"browser_url: {browser_url}")
    user_response = click.confirm(
        "Do you want to open the browser to continue the authorization process?"
    )
    if user_response:
        click.launch(f"{browser_url}")
        click.echo("Opening the browser...")
