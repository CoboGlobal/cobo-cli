import json
import logging
import time

import click
from click import BadParameter

from cobo_cli.data.context import CommandContext
from cobo_cli.managers import OrgTokenManager, UserTokenManager
from cobo_cli.utils.common import is_response_success

logger = logging.getLogger(__name__)


@click.group(
    "login",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to perform user or organization login operations. Use these commands to authenticate and retrieve tokens.",
)
@click.option(
    "--user",
    "-u",
    "login_type",
    help="Login action associated with user dimension. This is the default login type.",
    flag_value="user",
    default=True,
)
@click.option(
    "--org",
    "-o",
    "login_type",
    help="Login action associated with organization dimension.",
    flag_value="org",
)
@click.option(
    "--org-uuid",
    help="Specify the organization ID used to retrieve the token. Required for organization login.",
    required=False,
)
@click.option(
    "--refresh-token",
    is_flag=True,
    help="Refresh the existing token instead of generating a new one.",
)
@click.pass_context
def login(ctx, login_type, org_uuid, refresh_token):
    """
    Perform user or organization login operations.

    This command handles both user and organization login processes, including token refresh.
    """
    logger.debug(
        f"login command called. login_type selected: {login_type}, org_uuid: {org_uuid}"
    )
    if ctx.invoked_subcommand is None:
        command_context: CommandContext = ctx.obj
        config_manager = command_context.config_manager
        api_host = config_manager.get_config("api_host")

        if login_type == "user":
            perform_user_login(api_host, config_manager)
        elif login_type == "org":
            client_id = config_manager.get_config("client_id")
            app_key = config_manager.get_config("app_key")
            app_secret = config_manager.get_config("app_secret")

            if not all([client_id, app_key, app_secret]):
                raise click.ClickException(
                    "Missing required configuration. Please set CLIENT_ID, APP_KEY, and APP_SECRET."
                )

            perform_org_login(
                ctx,
                api_host,
                client_id,
                app_key,
                app_secret,
                org_uuid,
                refresh_token,
                config_manager,
            )
        else:
            raise click.ClickException(f"Invalid login type: {login_type}")


def perform_user_login(api_host: str, config_manager):
    """Handle user login process."""
    body = UserTokenManager.init_auth(api_host)
    if not is_response_success(body, stdout=True):
        return
    result = body.get("result", {})
    browser_url = result.get("browser_url")
    token_url = result.get("token_url")
    code = result.get("code")

    click.echo(f"browser_url: {browser_url}")
    click.echo(f"token_url: {token_url}")
    click.echo(f"code: " + click.style(f"{code}", fg="blue"))
    user_response = click.confirm(
        "Do you want to open the browser to continue the authorization process?"
    )
    if user_response:
        click.launch(f"{browser_url}")
        click.echo("Opening the browser...")

    click.echo("Polling the token URL for the granted token...")
    access_token = None
    for i in range(180):
        body = UserTokenManager.get_user_token(token_url)
        access_token = body.get("access_token")
        if access_token:
            config_manager.set_config("user_access_token", access_token)
            click.echo(
                f"Got token for user token: {access_token} on cobo cli, "
                f"saved to env file by using key: USER_ACCESS_TOKEN"
            )
            break
        time.sleep(1)
    if not access_token:
        click.echo("Login failed, please retry.")


def perform_org_login(
    ctx: click.Context,
    api_host: str,
    client_id: str,
    app_key: str,
    app_secret: str,
    org_uuid: str,
    refresh_token: bool,
    config_manager,
):
    """Handle organization login process."""
    if not org_uuid:
        raise BadParameter("--org-uuid must be provided to retrieve org token", ctx=ctx)

    try:
        if refresh_token:
            token_obj = refresh_org_token(
                api_host, client_id, app_key, app_secret, org_uuid, config_manager
            )
        else:
            token_obj = OrgTokenManager.get_token(
                api_host, client_id, app_key, app_secret, org_uuid
            )

        if not token_obj:
            raise click.ClickException("No token fetched, please check.")
        if token_obj.get("error"):
            raise click.ClickException(
                f"{token_obj['error']}, {token_obj.get('error_description')}"
            )

        config_manager.set_config(f"org_token_{org_uuid}", json.dumps(token_obj))
        click.echo(
            f"Got token for org {org_uuid}, saved to env file by using key: ORG_TOKEN_{org_uuid}"
        )
    except Exception as e:
        click.echo(f"{e}", err=True)


def refresh_org_token(
    api_host: str,
    client_id: str,
    app_key: str,
    app_secret: str,
    org_uuid: str,
    config_manager,
):
    """Refresh the organization token."""
    env_token_str = config_manager.get_config(f"org_token_{org_uuid}")
    if not env_token_str:
        raise click.ClickException("No refresh token found.")
    env_token_dict = json.loads(env_token_str)
    return OrgTokenManager.refresh_token(
        api_host,
        client_id,
        app_key,
        app_secret,
        org_uuid,
        env_token_dict["refresh_token"],
    )


if __name__ == "__main__":
    login()
