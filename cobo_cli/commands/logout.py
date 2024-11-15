import click
from dotenv import dotenv_values, get_key, set_key, unset_key

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.utils.api import make_request


@click.group(
    "logout",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to perform user or organization logout operations. "
    "Use these commands to remove authentication tokens.",
)
@click.option(
    "--user",
    "-u",
    "logout_type",
    help="Logout action associated with user dimension.",
    flag_value="user",
)
@click.option(
    "--org",
    "-o",
    "logout_type",
    help="Logout action associated with organization dimension.",
    flag_value="org",
)
@click.option(
    "--all",
    "-a",
    "logout_type",
    help="Logout action for both user and organization (default).",
    flag_value="all",
    default=True,
)
@click.pass_context
def logout(ctx, logout_type):
    """
    Perform user or organization logout operations.

    This command handles both user and organization logout processes,
    removing the respective tokens.
    """
    if ctx.invoked_subcommand is None:
        command_context: CommandContext = ctx.obj
        config_manager = command_context.config_manager

        if logout_type == "user":
            perform_user_logout(ctx, config_manager)
            click.echo("User access token removed.")
        elif logout_type == "org":
            perform_org_logout(ctx)
            click.echo("Organization access token removed.")
        else:  # "all" is the default
            perform_user_logout(ctx, config_manager)
            perform_org_logout(ctx)
            click.echo("All access tokens removed.")


def perform_user_logout(ctx, config_manager):
    """Handle user logout process."""
    make_request(ctx, "POST", "/oauth/token/logout", auth=AuthMethodType.USER)
    config_manager.delete_config("user_access_token")


def perform_org_logout(ctx):
    """Handle organization logout process."""
    make_request(ctx, "POST", "/oauth/token/logout", auth=AuthMethodType.ORG)
    current_org_uuid = get_key(".env", "CURRENT_ORG_UUID")  # Provide the .env file path
    if current_org_uuid:
        unset_key(".env", f"ORG_TOKEN_{current_org_uuid}")
        unset_key(".env", f"ORG_REFRESH_TOKEN_{current_org_uuid}")
        env_vars = dotenv_values(".env")
        for key, value in env_vars.items():
            if key.startswith("ORG_TOKEN_"):
                next_org_uuid = key[len("ORG_TOKEN_") :]
                set_key(".env", "CURRENT_ORG_UUID", next_org_uuid)
                click.echo(f"Switched to organization: {next_org_uuid}")
                return
        unset_key(".env", "CURRENT_ORG_UUID")


if __name__ == "__main__":
    logout()
