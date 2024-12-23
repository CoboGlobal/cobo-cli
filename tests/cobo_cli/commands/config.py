import os

import click

from cobo_cli.data.context import CommandContext


@click.group(
    "config",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Manage CLI configuration settings.",
)
@click.pass_context
def config(ctx: click.Context):
    """Manage CLI configuration settings."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@config.command("set")
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.pass_context
def set_config(ctx: click.Context, key: str, value: str):
    """Set a configuration value."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    if config_manager.set_config(key, value):
        click.echo(f"Configuration '{key}' set to '{value}'")
    else:
        click.echo(
            f"Failed to set configuration '{key}'. Make sure it's a valid configuration key."
        )


@config.command("get")
@click.argument("key", type=str)
@click.pass_context
def get_config(ctx: click.Context, key: str):
    """Get a configuration value."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    value = config_manager.get_config(key)
    if value is not None:
        click.echo(f"{key}: {value}")
    else:
        click.echo(f"Configuration '{key}' not found")


@config.command("list")
@click.pass_context
def list_config(ctx: click.Context):
    """List all configuration values."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    configs = config_manager.list_configs()
    if configs:
        for key, value in configs.items():
            click.echo(f"{key}: {value}")
    else:
        click.echo("No configurations found")


@config.command("delete")
@click.argument("key", type=str)
@click.pass_context
def delete_config(ctx: click.Context, key: str):
    """Delete a configuration value."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    if config_manager.delete_config(key):
        click.echo(f"Configuration '{key}' deleted")
    else:
        click.echo(f"Configuration '{key}' not found or cannot be deleted")


@config.command("show-path")
@click.pass_context
def show_config_path(ctx: click.Context):
    """Show the configuration file path."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    absolute_path = os.path.abspath(config_manager.config_file)
    click.echo(f"Configuration file path: {absolute_path}")


if __name__ == "__main__":
    config()
