import logging

# Import version from pyproject.toml
from importlib.metadata import version as get_version

import click

from cobo_cli.commands import (
    app,
    auth,
    config,
    delete_api,
    doc,
    env,
    get_api,
    graphql,
    keys,
    login,
    logout,
    logs,
    open,
    post_api,
    put_api,
    webhook,
)
from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.utils.api import load_api_spec
from cobo_cli.utils.config import ConfigManager

logger = logging.getLogger(__name__)


def setup_logging(enable_debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if enable_debug else logging.INFO,
        format="%(levelname)s\t%(asctime)s\t[%(name)s] %(message)s",
    )


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "-e",
    "--env",
    "env_type",
    type=click.Choice(EnvironmentType.values()),
    help="Override the environment for this command.",
)
@click.option(
    "-a",
    "--auth",
    "auth_type",
    type=click.Choice(AuthMethodType.values()),
    help="Override the authentication method for this command.",
)
@click.option(
    "--enable-debug", is_flag=True, help="Enable debug mode for verbose logging."
)
@click.option(
    "--config-file",
    default=ConfigManager.get_config_file_path(),
    help="Specify the path to the config file. Example: --config-file /path/to/config.toml",
)
@click.option(
    "--spec",
    "custom_spec_path",
    type=click.Path(exists=True),
    help="Path to a custom OpenAPI specification file",
)
@click.pass_context
def cli(
    ctx: click.Context,
    env_type: str,
    auth_type: str,
    enable_debug: bool,
    config_file: str,
    custom_spec_path: str,
) -> None:
    """Cobo CLI - A command-line interface for managing Cobo applications and configurations."""
    setup_logging(enable_debug)

    config_manager = ConfigManager(config_file, env_type)

    # If current_env is not specified, try to load it from the config
    if not env_type:
        env_type = config_manager.get_config("environment")

    # If current_env is still not set, default to 'dev'
    env_type = env_type or EnvironmentType.DEVELOPMENT.value

    # If auth_type is not specified, try to load it from the config
    if not auth_type:
        auth_type = config_manager.get_config("auth_method")

    auth_type = auth_type or AuthMethodType.APIKEY.value

    # Load API spec
    api_spec = load_api_spec(custom_spec_path) if custom_spec_path else None

    # Create CommandContext and store it in ctx.obj
    ctx.obj = CommandContext(
        env=EnvironmentType(env_type),
        auth_method=AuthMethodType(auth_type),
        config_manager=config_manager,
        api_spec=api_spec,
    )

    logger.debug(
        f"MainCommand called with parameters: "
        f"environment={env_type}, auth={auth_type}, "
        f"config_file={config_file}, "
        f"custom_spec_path={custom_spec_path}"
    )
    logger.debug(f"Command context obj: {ctx.obj}")


@cli.command("version", help="Display the current version of the Cobo CLI tool.")
def version():
    """Display the current version of the Cobo CLI tool."""
    click.echo(f"Cobo CLI version: {get_version('cobo-cli')}")


# Add subcommands
cli.add_command(config)
cli.add_command(login)
cli.add_command(logout)
cli.add_command(keys)
cli.add_command(app)
cli.add_command(open)
cli.add_command(doc)
cli.add_command(env)
cli.add_command(logs)
cli.add_command(auth)
cli.add_command(webhook)

# Add API commands
cli.add_command(get_api, name="get")
cli.add_command(post_api, name="post")
cli.add_command(put_api, name="put")
cli.add_command(delete_api, name="delete")
cli.add_command(graphql, name="graphql")  # Add this line

if __name__ == "__main__":
    cli()
