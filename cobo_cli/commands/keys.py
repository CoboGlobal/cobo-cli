import logging

import click

from cobo_cli.data.context import CommandContext
from cobo_cli.managers import KeysManager

logger = logging.getLogger(__name__)


@click.group(
    "keys",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to generate and manage API/APP keys. Use these commands to create new keys or manage existing ones.",
)
@click.pass_context
def keys(ctx: click.Context):
    """Key management command group."""
    pass


@keys.command("generate", help="Generate a new API/APP key pair.")
@click.option(
    "--key-type",
    type=click.Choice(["API", "APP"]),
    default="API",
    help="Type of key to generate (API or APP).",
)
@click.option(
    "--alg",
    default="ed25519",
    help="Specify the key generation algorithm.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force to replace existing keys.",
)
@click.pass_context
def generate_keys(ctx: click.Context, key_type: str, alg: str, force: bool):
    """Generate a new API/APP key pair."""
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager

    logger.debug(
        f"Generating keys using the following options, key_type: {key_type}, "
        f"algorithm: {alg}, force: {force}"
    )

    current_env = config_manager.get_config("environment")
    key_config = f"{key_type.lower()}_key"
    secret_config = f"{key_type.lower()}_secret"

    if config_manager.get_config(key_config):
        if not force:
            raise click.ClickException(
                f"--force must be used when {key_type} key exists."
            )

    try:
        secret, pubkey = KeysManager.generate(alg)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Save the keys in the correct environment section
    config_manager.set_config(key_config, pubkey)
    config_manager.set_config(secret_config, secret)

    # Avoid logging sensitive information
    click.echo(f"{key_type} key generation successful.")
    click.echo(f"Public key: {pubkey}")
    click.echo(f"Secret key has been saved securely in the {current_env} environment section.")


if __name__ == "__main__":
    keys()
