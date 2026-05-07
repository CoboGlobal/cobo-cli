import os
import shlex

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


# (env_var_name, settings_attr) — single source of truth for export list
ENV_EXPORT = [
    ("COBO_ENV", "environment"),
    ("COBO_API_SECRET", "api_secret"),
    ("COBO_API_KEY", "api_key"),
    ("COBO_API_HOST", "api_host"),
]


def _format_shell(name: str, value: str) -> str:
    return f"export {name}={shlex.quote(value)}"


def _format_powershell(name: str, value: str) -> str:
    safe = str(value).replace("'", "''")
    return f"$env:{name} = '{safe}'"


def _format_cmd(name: str, value: str) -> str:
    escaped = str(value).replace("^", "^^").replace('"', '^"')
    return f'set "{name}={escaped}"'


_ENV_FORMATTERS = {
    "shell": _format_shell,
    "powershell": _format_powershell,
    "cmd": _format_cmd,
}


@config.command("env")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["shell", "powershell", "cmd"]),
    default="shell",
    help="Output format: shell (bash/zsh), powershell, or cmd (Windows CMD).",
)
@click.pass_context
def config_env(ctx: click.Context, fmt: str):
    """Print env vars from current config for use in your shell.

    macOS/Linux (bash/zsh):  eval $(cobo config env)
    Windows PowerShell:      cobo config env --format powershell | Invoke-Expression
    Windows CMD:            cobo config env --format cmd > env.bat && env.bat
    """
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    formatter = _ENV_FORMATTERS[fmt]
    for name, attr in ENV_EXPORT:
        value = getattr(config_manager.settings, attr, None)
        if value is not None:
            click.echo(formatter(name, value))


if __name__ == "__main__":
    config()
