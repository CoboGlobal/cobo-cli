import click

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext


@click.command(
    "auth",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Set or view the default authentication method.",
)
@click.argument("method", type=click.Choice(AuthMethodType.values()), required=False)
@click.pass_context
def auth(ctx: click.Context, method: str):
    """Set or view the default authentication method."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager

    if method:
        config_manager.set_config("auth_method", method)
        click.echo(f"Default authentication method set to: {method}")
    else:
        current_method = config_manager.get_config(
            "auth_method", AuthMethodType.APIKEY.value
        )
        click.echo(f"Current default authentication method: {current_method}")


if __name__ == "__main__":
    auth()
