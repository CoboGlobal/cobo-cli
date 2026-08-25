"""Local TSS Node management on top of Docker.

A server co-signer is one Docker container plus four host directories. The
official ``tss-node.sh`` wrapper drives the same container interactively; this
module drives it through the binary's own ``--key-file`` flag instead, so every
operation also works with no terminal attached -- the way an AI agent runs.

The node's key share lives in ``db/secrets.db`` under the node home, encrypted
with the password. Losing either the file or the password loses the share.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

# Pinned so that every user of this CLI version runs the same node build. The
# official wrapper script pins the same way (VERSION= in tss-node.sh).
DEFAULT_IMAGE = "coboglobal/tss-node:v0.12.20"

DATA_DIRS = ("configs", "db", "logs", "recovery")

# The node's own config only distinguishes these two; the CLI's dev and
# sandbox environments both map to the development relay.
ENV_TO_NODE_ENV = {"prod": "production", "dev": "development", "sandbox": "development"}

CONTAINER_KEY_FILE = "/app/secret/key"
CONTAINER_CA_FILE = "/etc/cobo-extra-ca.pem"


class TssNodeError(Exception):
    """Raised for conditions the caller should surface verbatim."""


def node_home(environment: str) -> Path:
    return Path.home() / ".cobo" / "tss-node" / environment


def container_name(environment: str) -> str:
    return f"cobo-tss-node-{environment}"


def ensure_docker() -> None:
    if shutil.which("docker") is None:
        raise TssNodeError(
            "Docker is required to run a TSS Node but was not found on PATH. "
            "Install Docker and try again."
        )
    probe = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        raise TssNodeError(
            "Docker is installed but the daemon is not reachable. Start Docker "
            "and try again."
        )


def prepare_home(environment: str) -> Path:
    home = node_home(environment)
    for name in DATA_DIRS:
        (home / name).mkdir(mode=0o700, parents=True, exist_ok=True)
    node_env = ENV_TO_NODE_ENV[environment]
    config = home / "configs" / "cobo-tss-node-config.yaml"
    if not config.exists():
        config.write_text(f"env: {node_env}\n")
    return home


def run_args(
    environment: str,
    command: List[str],
    key_file: Path,
    image: str,
    detach: bool = False,
    ca_bundle: Optional[Path] = None,
) -> List[str]:
    """Compose the docker invocation for one node command.

    The password reaches the container only as a read-only file mount; it never
    appears in argv, where any user on the machine could read it from ``ps``.
    """
    home = node_home(environment)
    uid = subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip()
    gid = subprocess.run(["id", "-g"], capture_output=True, text=True).stdout.strip()
    args = ["docker", "run", "--user", f"{uid}:{gid}"]
    args += ["-d", "--name", container_name(environment)] if detach else ["--rm"]
    for name in DATA_DIRS:
        args += ["-v", f"{home / name}:/app/{name}"]
    args += ["-v", f"{key_file}:{CONTAINER_KEY_FILE}:ro"]
    if ca_bundle is not None:
        args += [
            "-v",
            f"{ca_bundle}:{CONTAINER_CA_FILE}:ro",
            "--env",
            f"SSL_CERT_FILE={CONTAINER_CA_FILE}",
        ]
    args += [image]
    args += command
    args += ["--key-file", CONTAINER_KEY_FILE]
    return args


def container_state(environment: str) -> Optional[dict]:
    """Return docker's view of the node container, or None when absent."""
    result = subprocess.run(
        ["docker", "inspect", container_name(environment)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)[0]


def relay_state(environment: str, tail: int = 40) -> str:
    """Summarize the relay connection from recent container logs.

    The node retries forever, so the latest matching line is the truth. The
    strings matched here are the three states a fresh operator meets: connected,
    refused because the node is not yet in any key share holder group, and TLS
    interception by a corporate proxy.
    """
    result = subprocess.run(
        ["docker", "logs", "--tail", str(tail), container_name(environment)],
        capture_output=True,
        text=True,
    )
    lines = (result.stdout + result.stderr).splitlines()
    for line in reversed(lines):
        if "connected." in line:
            return "connected to the relay"
        if "not bound to any app" in line or "invalid node ID" in line:
            return (
                "running, waiting to be added to a key share holder group "
                "(the relay refuses unbound nodes; this resolves once the "
                "group is created)"
            )
        if "certificate signed by unknown authority" in line:
            return (
                "cannot reach the relay: TLS is intercepted by a proxy the "
                "container does not trust. Re-run `cobo node start` with "
                "--ca-bundle pointing at your proxy's CA bundle."
            )
    return "no relay activity in recent logs"


def parse_node_id(output: str) -> Optional[str]:
    for line in output.splitlines():
        if "Node ID:" in line:
            return line.split("Node ID:", 1)[1].split()[0]
    return None
