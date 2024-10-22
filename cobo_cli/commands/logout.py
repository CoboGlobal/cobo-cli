import click

from cobo_cli.data.context import CommandContext


@click.group(
    "logout",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to perform user or organization logout operations. Use these commands to remove authentication tokens.",
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

    This command handles both user and organization logout processes, removing the respective tokens.
    """
    if ctx.invoked_subcommand is None:
        command_context: CommandContext = ctx.obj
        config_manager = command_context.config_manager

        if logout_type == "user":
            perform_user_logout(config_manager)
        elif logout_type == "org":
            perform_org_logout(config_manager)
        else:  # "all" is the default
            perform_all_logout(config_manager)


def perform_user_logout(config_manager):
    """Handle user logout process."""
    config_manager.delete_config("user_access_token")
    click.echo("User access token removed.")


def perform_org_logout(config_manager):
    """Handle organization logout process."""
    config_manager.delete_config("org_access_token")
    click.echo("Organization access token removed.")


def perform_all_logout(config_manager):
    """Handle logout for both user and organization."""
    if config_manager.get_config("user_access_token"):
        config_manager.delete_config("user_access_token")
    if config_manager.get_config("org_access_token"):
        config_manager.delete_config("org_access_token")
    click.echo("All access tokens removed.")


if __name__ == "__main__":
    logout()
