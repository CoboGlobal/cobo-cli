import click

from cobo_cli.data.context import CommandContext


@click.command(
    "open",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Open a specific Cobo portal page in the default web browser.",
)
@click.argument(
    "target",
    default="portal",
    type=click.Choice(
        [
            "portal",
            "dashboard",
            "wallets",
            "custodial",
            "mpc",
            "scw",
            "exchange",
            "developer",
            "apps",
            "pricing",
            "approval",
        ]
    ),
)
@click.pass_context
def open(ctx: click.Context, target: str):
    """Open a specific Cobo portal page in the default web browser."""
    command_context: CommandContext = ctx.obj
    base_url = command_context.config_manager.get_config("base_url").rstrip("/")

    url_mapping = {
        "portal": "",
        "dashboard": "dashboard",
        "wallets": "wallets",
        "custodial": "wallets/management/custodial",
        "mpc": "wallets/management/mpc",
        "scw": "wallets/management/smartContract",
        "exchange": "wallets/management/exchanges",
        "tx": "wallets/transaction",
        "rc": "wallets/riskControl",
        "address": "wallets/addressBook",
        "developer": "developers",
        "apps": "apps",
        "org": "org",
        "members": "org/members",
        "fee": "org/fee-station",
        "roles": "org/roles",
        "governance": "org/policies",
        "activities": "org/activities",
        "pricing": "payment/pricingPlans",
        "approval": "notifications/approvals/pending-my-approval",
    }

    if target in url_mapping:
        url = f"{base_url}/{url_mapping[target]}"
        click.echo(f"Opening {target} page in your default browser...")
        click.echo(f"URL: {url}")
        click.launch(url)
    else:
        click.echo(f"Unknown target: {target}")


if __name__ == "__main__":
    open()
