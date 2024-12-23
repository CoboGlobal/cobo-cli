import click

from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType


@click.command(
    "env",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Set or view the current environment.",
)
@click.argument(
    "environment", type=click.Choice(EnvironmentType.values()), required=False
)
@click.pass_context
def env(ctx: click.Context, environment: str):
    """Set or view the current environment."""
    command_context: CommandContext = ctx.obj

    if not isinstance(command_context, CommandContext):
        raise click.ClickException("Command context not properly initialized.")

    config_manager = command_context.config_manager

    if environment:
        config_manager.set_config("environment", environment)
        click.echo(f"Environment set to: {environment}")
    else:
        current_env = config_manager.get_config(
            "environment", EnvironmentType.DEVELOPMENT.value
        )
        click.echo(f"Current environment: {current_env}")


if __name__ == "__main__":
    env()
