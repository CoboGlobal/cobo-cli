import logging
import os

import click
from dotenv import dotenv_values, get_key, load_dotenv, set_key

from cobo_cli.commands.logout import perform_user_logout
from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.utils.api import make_request
from cobo_cli.utils.app import (
    app_directory_with_env_file,
    is_app_directory,
    validate_manifest_and_get_app_id,
)
from cobo_cli.utils.authorization import (
    handle_browser_interaction,
    initiate_auth,
    is_response_success,
    poll_for_token,
)

logger = logging.getLogger(__name__)


def get_logged_in_orgs():
    """
    Utility function to get all logged-in organization UUIDs.
    """
    env_vars = dotenv_values(".env")
    return {
        key.replace("ORG_TOKEN_", ""): value
        for key, value in env_vars.items()
        if key.startswith("ORG_TOKEN_")
    }


@click.group(
    "login",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help=(
        "Commands to perform user or organization login operations. "
        "Use these commands to authenticate and retrieve tokens."
    ),
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
    "--refresh-token",
    is_flag=True,
    help="Refresh the existing token instead of generating a new one.",
)
@click.pass_context
def login(ctx, login_type, refresh_token):
    """
    Perform user or organization login operations.

    This command handles both user and organization login processes, including token refresh.
    """
    # Check if a subcommand is being invoked
    if ctx.invoked_subcommand is not None:
        return  # Do not execute the login logic if a subcommand is invoked

    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager

    if login_type == "user":
        # Check if user is already logged in
        existing_token = config_manager.get_config("user_access_token")
        if existing_token:
            click.echo("You are already logged in.")
            if click.confirm("Do you want to logout before re-login?"):
                perform_user_logout(ctx, config_manager)
            else:
                return

        # Step 1: Initiate user authentication
        body = initiate_auth(ctx, "cobo_cli")

        if not is_response_success(body, stdout=True):
            return

        result = body.get("result", {})
        browser_url = result.get("browser_url")
        token_url = result.get("token_url")

        # Step 2: Handle browser interaction
        handle_browser_interaction(browser_url)

        # Step 3: Poll for the token
        token_response = poll_for_token(ctx, token_url, auth_method=AuthMethodType.USER)
        access_token = token_response.get("access_token")

        if access_token:
            config_manager.set_config("user_access_token", access_token)
            click.echo(
                f"Got token for user: {access_token} on cobo cli, "
                f"saved to config file by using key: USER_ACCESS_TOKEN"
            )
        else:
            click.echo("Login failed, please retry.")

    elif login_type == "org":
        if not app_directory_with_env_file():
            return

        # Load environment variables
        load_dotenv()

        # Load the manifest
        manifest, _ = validate_manifest_and_get_app_id(ctx, require_app_id=False)

        # Determine the correct client_id based on the environment
        if ctx.obj.env == EnvironmentType.PRODUCTION:
            client_id = manifest.client_id
        else:
            client_id = manifest.dev_client_id

        app_key = manifest.app_key
        app_secret = get_key(".env", "APP_SECRET")  # Provide the .env file path

        if not all([client_id, app_key, app_secret]):
            raise click.ClickException(
                "Missing required configuration. "
                "Please ensure CLIENT_ID, APP_KEY, and APP_SECRET are set in the manifest and .env file."
            )
        if refresh_token:
            org_uuid = get_key(".env", "CURRENT_ORG_UUID")  # Provide the .env file path
            if not org_uuid:
                raise click.ClickException(
                    "No current organization set. Please login to an organization first."
                )

            # Refresh the organization token
            refresh_token_value = get_key(
                ".env", f"ORG_REFRESH_TOKEN_{org_uuid}"
            )  # Provide the .env file path
            if not refresh_token_value:
                raise click.ClickException(
                    "No refresh token found. Please login first."
                )

            params = {
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_value,
            }
            api_path = "/oauth/token"

            response = make_request(
                ctx, "POST", api_path, json=params, auth=AuthMethodType.ORG
            )
            token_obj = response.json()

            if not token_obj.get("access_token"):
                raise click.ClickException(
                    "Failed to refresh token, please check the refresh token and try again."
                )

            # Save the new org token in the .env file
            set_key(".env", f"ORG_TOKEN_{org_uuid}", token_obj["access_token"])
            set_key(
                ".env",
                f"ORG_REFRESH_TOKEN_{org_uuid}",
                token_obj.get("refresh_token", refresh_token_value),
            )
            click.echo(
                f"Organization access token refreshed successfully for org: {org_uuid}"
            )
        else:
            # Perform organization login
            try:
                # Step 1: Initiate organization authentication
                body = initiate_auth(ctx, client_id, "org")

                if not is_response_success(body, stdout=True):
                    return

                result = body.get("result", {})
                browser_url = result.get("browser_url")
                token_url = result.get("token_url")

                # Step 2: Handle browser interaction
                handle_browser_interaction(browser_url)

                # Step 3: Poll for the token
                token_obj = poll_for_token(
                    ctx, token_url, auth_method=AuthMethodType.ORG
                )

                if not token_obj:
                    raise click.ClickException("No token fetched, please check.")
                if token_obj.get("error"):
                    raise click.ClickException(
                        f"{token_obj['error']}, {token_obj.get('error_description')}"
                    )

                access_token = token_obj.get("access_token")
                refresh_token_value = token_obj.get("refresh_token")
                org_uuid = token_obj.get("org_id")

                # Save the org token in the .env file
                set_key(".env", f"ORG_TOKEN_{org_uuid}", access_token)
                set_key(".env", f"ORG_REFRESH_TOKEN_{org_uuid}", refresh_token_value)
                set_key(".env", "CURRENT_ORG_UUID", org_uuid)
                click.echo(
                    f"Got token for org {org_uuid}, saved to .env file with key: ORG_TOKEN_{org_uuid}"
                )
            except Exception as e:
                click.echo(f"{e}", err=True)

    else:
        raise click.ClickException(f"Invalid login type: {login_type}")


@login.command("status", help="Show the current login status.")
@click.pass_context
def login_status(ctx):
    """
    Display the current login status for user and organization.
    """
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager

    user_token = config_manager.get_config("user_access_token")
    if user_token:
        click.echo("User is logged in.")
    else:
        click.echo("User is not logged in.")

    if not is_app_directory():
        click.echo("Not in an app directory. No manifest.json found.")
        return

    if not os.path.isfile(".env"):
        click.echo(
            "App directory detected, You may need to login to an organization first via 'cobo login --org' command."
        )
        return

    env_vars = dotenv_values(".env")
    org_tokens = get_logged_in_orgs()
    current_org_uuid = env_vars.get("CURRENT_ORG_UUID")

    if org_tokens:
        click.echo("Organization tokens found:")
        for org_uuid in org_tokens:
            if org_uuid == current_org_uuid:
                click.echo(f" - {org_uuid} (current)")
            else:
                click.echo(f" - {org_uuid}")
        click.echo(
            "\nYou can use 'cobo login switch-org' command to switch between organizations."
        )
    else:
        click.echo("No organization tokens found.")


@login.command("switch-org", help="Switch between logged-in organizations.")
@click.pass_context
def switch_org(ctx):
    """
    List all logged-in organization UUIDs and allow the user to switch between them.
    """
    if not app_directory_with_env_file():
        return

    org_tokens = get_logged_in_orgs()
    current_org_uuid = dotenv_values(".env").get("CURRENT_ORG_UUID")

    if not org_tokens:
        click.echo(
            "No organization tokens found. Please login to an organization first."
        )
        return

    click.echo("Available organizations:")
    for idx, org_uuid in enumerate(org_tokens.keys(), start=1):
        if org_uuid == current_org_uuid:
            click.echo(f"{idx}. {org_uuid} (current)")
        else:
            click.echo(f"{idx}. {org_uuid}")

    choice = click.prompt(
        "Enter the number of the organization you want to switch to", type=int
    )

    if 1 <= choice <= len(org_tokens):
        selected_org_uuid = list(org_tokens.keys())[choice - 1]
        set_key(".env", "CURRENT_ORG_UUID", selected_org_uuid)
        click.echo(f"Switched to organization: {selected_org_uuid}")
    else:
        click.echo("Invalid choice. No changes made.")


if __name__ == "__main__":
    login()
