"""`cobo node` -- run and manage a local TSS Node (server co-signer).

The node is the second key share holder for an Org-Controlled MPC vault. With
one running locally, the whole MPC setup -- vault, key share holder group,
keygen -- completes over the API with no phone and no human, which is what
makes the path automatable for AI agents.
"""

import subprocess
from pathlib import Path

import click

from cobo_cli.data.context import CommandContext
from cobo_cli.utils.tss_node import (
    DEFAULT_IMAGE,
    TssNodeError,
    container_name,
    container_state,
    ensure_docker,
    node_home,
    parse_node_id,
    prepare_home,
    relay_state,
    run_args,
)


def _environment(ctx: click.Context) -> str:
    command_context: CommandContext = ctx.obj
    return command_context.env.value


def _resolve_key_file(key_file: str) -> Path:
    """Return the password file to mount.

    The password is taken as a file rather than an option value so it can never
    show up in shell history or `ps` output.
    """
    if key_file:
        path = Path(key_file).expanduser()
        if not path.is_file():
            raise click.ClickException(f"Key file not found: {path}")
        return path
    raise click.ClickException(
        "A database password is required. Pass --key-file with a file "
        "containing the password (16-32 characters). Keep that file: together "
        "with db/secrets.db it is the key share."
    )


def _run(args, capture=False):
    return subprocess.run(args, capture_output=capture, text=True)


@click.group(
    "node",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Run and manage a local TSS Node (server co-signer) for MPC wallets.",
)
def node():
    """Manage a local TSS Node."""


@node.command("init", help="Initialize a local TSS Node identity.")
@click.option(
    "--key-file",
    default=None,
    help="File containing the database password (16-32 characters). "
    "The password encrypts the node's key share; never passed as a value.",
)
@click.option("--image", default=DEFAULT_IMAGE, show_default=True)
@click.pass_context
def node_init(ctx, key_file, image):
    environment = _environment(ctx)
    try:
        ensure_docker()
    except TssNodeError as e:
        raise click.ClickException(str(e))
    home = prepare_home(environment)
    if (home / "db" / "secrets.db").exists():
        raise click.ClickException(
            f"A node is already initialized under {home}. Use `cobo node info` "
            "to inspect it; initializing again would create a second identity, "
            "not recover the first."
        )
    key_path = _resolve_key_file(key_file)
    result = _run(run_args(environment, ["init"], key_path, image), capture=True)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise click.ClickException(f"Node initialization failed:\n{output[-800:]}")
    node_id = parse_node_id(output)
    if node_id:
        (home / "node_id").write_text(node_id + "\n")
    click.echo(f"TSS Node initialized under {home}")
    click.echo(f"Node ID: {node_id or '(not found in output -- see `cobo node info`)'}")
    click.echo()
    click.echo(
        "Back up db/secrets.db together with your password file now; they are "
        "the key share. Losing either loses every wallet this node co-signs "
        "for."
    )
    click.echo(
        "Next: start the node (`cobo node start`), then create a key share "
        "holder group carrying this node ID -- POST "
        "/v2/wallets/mpc/vaults/{vault_id}/key_share_holder_groups. The node "
        "registers itself when the group is created."
    )


@node.command("start", help="Start the local TSS Node in the background.")
@click.option("--key-file", default=None, help="File containing the database password.")
@click.option("--image", default=DEFAULT_IMAGE, show_default=True)
@click.option(
    "--ca-bundle",
    default=None,
    help="Extra CA bundle for networks where TLS is intercepted by a proxy "
    "(the container must trust the proxy's CA to reach Cobo's relay).",
)
@click.pass_context
def node_start(ctx, key_file, image, ca_bundle):
    environment = _environment(ctx)
    try:
        ensure_docker()
    except TssNodeError as e:
        raise click.ClickException(str(e))
    home = prepare_home(environment)
    if not (home / "db" / "secrets.db").exists():
        raise click.ClickException(
            f"No node is initialized under {home}. Run `cobo node init` first."
        )
    if container_state(environment) is not None:
        raise click.ClickException(
            f"Container {container_name(environment)} already exists. Use "
            "`cobo node status` to check it or `cobo node stop` to remove it."
        )
    key_path = _resolve_key_file(key_file)
    ca_path = None
    if ca_bundle:
        ca_path = Path(ca_bundle).expanduser()
        if not ca_path.is_file():
            raise click.ClickException(f"CA bundle not found: {ca_path}")
    result = _run(
        run_args(
            environment,
            ["start"],
            key_path,
            image,
            detach=True,
            ca_bundle=ca_path,
        ),
        capture=True,
    )
    if result.returncode != 0:
        raise click.ClickException(f"Failed to start:\n{result.stderr[-500:]}")
    click.echo(f"TSS Node started ({container_name(environment)}).")
    click.echo(
        "A node that is not yet in any key share holder group is refused by "
        "the relay and keeps retrying; that is the expected state until the "
        "group is created. Check with `cobo node status`."
    )


@node.command("status", help="Show container and relay state of the local node.")
@click.pass_context
def node_status(ctx):
    environment = _environment(ctx)
    home = node_home(environment)
    node_id_file = home / "node_id"
    if node_id_file.exists():
        click.echo(f"Node ID: {node_id_file.read_text().strip()}")
    state = container_state(environment)
    if state is None:
        initialized = (home / "db" / "secrets.db").exists()
        click.echo(
            "Container: not running"
            + ("" if initialized else " (node not initialized -- run `cobo node init`)")
        )
        return
    click.echo(f"Container: {state['State']['Status']}")
    if state["State"]["Status"] == "running":
        click.echo(f"Relay: {relay_state(environment)}")


@node.command("stop", help="Stop and remove the local node container.")
@click.pass_context
def node_stop(ctx):
    environment = _environment(ctx)
    if container_state(environment) is None:
        click.echo("Container is not running; nothing to stop.")
        return
    result = _run(["docker", "rm", "-f", container_name(environment)], capture=True)
    if result.returncode != 0:
        raise click.ClickException(f"Failed to stop:\n{result.stderr[-300:]}")
    click.echo(
        "Node stopped. The key share stays in db/secrets.db; `cobo node start` "
        "resumes with the same identity."
    )


@node.command("logs", help="Show recent logs of the local node.")
@click.option("--tail", default=50, show_default=True)
@click.pass_context
def node_logs(ctx, tail):
    environment = _environment(ctx)
    if container_state(environment) is None:
        raise click.ClickException("Container does not exist.")
    result = _run(
        ["docker", "logs", "--tail", str(tail), container_name(environment)],
        capture=True,
    )
    click.echo(result.stdout + result.stderr)


@node.command("info", help="Show the node's identity from its database.")
@click.option("--key-file", default=None, help="File containing the database password.")
@click.option("--image", default=DEFAULT_IMAGE, show_default=True)
@click.pass_context
def node_info(ctx, key_file, image):
    environment = _environment(ctx)
    try:
        ensure_docker()
    except TssNodeError as e:
        raise click.ClickException(str(e))
    home = node_home(environment)
    if not (home / "db" / "secrets.db").exists():
        raise click.ClickException(
            f"No node is initialized under {home}. Run `cobo node init` first."
        )
    key_path = _resolve_key_file(key_file)
    result = _run(run_args(environment, ["info"], key_path, image), capture=True)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise click.ClickException(f"Failed to read node info:\n{output[-500:]}")
    click.echo(output.strip())
