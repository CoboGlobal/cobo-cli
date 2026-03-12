import shutil
from pathlib import Path
from typing import Dict

import click

# Supported AI coding agents and their skill directory names
AGENT_SKILL_DIRS: Dict[str, str] = {
    "claude": ".claude",
    "cursor": ".cursor",
}

AGENT_DISPLAY_NAMES: Dict[str, str] = {
    "claude": "Claude Code",
    "cursor": "Cursor",
}

SKILL_NAME = "cobo-waas"


def _get_skill_path(agent: str, scope: str) -> Path:
    """Get the skill installation path for an agent and scope."""
    agent_dir = AGENT_SKILL_DIRS[agent]
    if scope == "global":
        return Path.home() / agent_dir / "skills" / SKILL_NAME
    else:  # local
        return Path.cwd() / agent_dir / "skills" / SKILL_NAME


def _get_all_skill_paths(agent: str) -> Dict[str, Path]:
    """Get both global and local paths for an agent."""
    return {
        "global": _get_skill_path(agent, "global"),
        "local": _get_skill_path(agent, "local"),
    }


@click.group(
    "skill",
    invoke_without_command=True,
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Install and manage AI coding agent skills.",
)
@click.pass_context
def skill(ctx: click.Context):
    """Install and manage AI coding agent skills."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@skill.command("install")
@click.argument("agent", type=click.Choice(["claude", "cursor", "all"]))
@click.option(
    "-s",
    "--scope",
    type=click.Choice(["global", "local"]),
    default="global",
    help="Installation scope: 'global' (~/.claude/skills) or 'local' (./.claude/skills in current project)",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite existing skill")
def install(agent: str, scope: str, force: bool):
    """Install cobo-waas skill for an AI coding agent.

    AGENT can be: claude, cursor, or all

    \b
    Examples:
      cobo skill install claude              # Install globally for Claude Code
      cobo skill install claude --scope local  # Install in current project
      cobo skill install all                 # Install globally for all agents
    """
    skill_src = _get_package_skill_path()

    if agent == "all":
        agents = list(AGENT_SKILL_DIRS.keys())
    else:
        agents = [agent]

    for agent_name in agents:
        target = _get_skill_path(agent_name, scope)
        display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
        scope_label = "global" if scope == "global" else "project"

        if target.exists() and not force:
            click.echo(f"Skill already exists at {target}. Use --force to overwrite.")
            continue

        # Create parent directory if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing skill if force is set
        if target.exists():
            shutil.rmtree(target)

        # Copy skill files
        shutil.copytree(skill_src, target)
        click.echo(f"Installed {SKILL_NAME} ({scope_label}) for {display_name}")
        click.echo(f"  Path: {target}")


@skill.command("list")
def list_skills():
    """List available skills."""
    click.echo("Available skills:")
    click.echo(f"  {SKILL_NAME} - Cobo WaaS 2.0 API operations for AI coding agents")
    click.echo("")
    click.echo("Supported agents: claude, cursor")
    click.echo("")
    click.echo("Usage:")
    click.echo("  cobo skill install claude                # Install globally")
    click.echo("  cobo skill install claude --scope local  # Install in project")
    click.echo("  cobo skill install all                   # Install for all agents")


@skill.command("remove")
@click.argument("agent", type=click.Choice(["claude", "cursor", "all"]))
@click.option(
    "-s",
    "--scope",
    type=click.Choice(["global", "local", "all"]),
    default="all",
    help="Which installation to remove: 'global', 'local', or 'all' (default)",
)
def remove(agent: str, scope: str):
    """Remove installed skill from an AI coding agent.

    AGENT can be: claude, cursor, or all

    \b
    Examples:
      cobo skill remove claude              # Remove all installations for Claude
      cobo skill remove claude --scope global  # Remove only global installation
      cobo skill remove all                 # Remove from all agents
    """
    if agent == "all":
        agents = list(AGENT_SKILL_DIRS.keys())
    else:
        agents = [agent]

    scopes_to_check = ["global", "local"] if scope == "all" else [scope]

    for agent_name in agents:
        display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
        removed_any = False

        for s in scopes_to_check:
            target = _get_skill_path(agent_name, s)
            if target.exists():
                shutil.rmtree(target)
                click.echo(f"Removed {SKILL_NAME} ({s}) from {display_name}")
                removed_any = True

        if not removed_any:
            click.echo(f"No skill installed for {display_name}")


@skill.command("status")
def status():
    """Show skill installation status."""
    click.echo("Skill installation status:")
    click.echo("")

    for agent_name in AGENT_SKILL_DIRS.keys():
        display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
        paths = _get_all_skill_paths(agent_name)

        global_installed = paths["global"].exists()
        local_installed = paths["local"].exists()

        click.echo(f"  {display_name}:")

        if global_installed:
            click.echo("    Global: Installed")
            click.echo(f"      Path: {paths['global']}")
        else:
            click.echo("    Global: Not installed")

        if local_installed:
            click.echo("    Local:  Installed")
            click.echo(f"      Path: {paths['local']}")
        else:
            click.echo(f"    Local:  Not installed (would be at {paths['local']})")

        click.echo("")


def _get_package_skill_path() -> Path:
    """Get the path to skills bundled with the package."""
    # Method 1: Development mode (skills/ in repo root)
    dev_path = Path(__file__).parent.parent.parent / "skills" / SKILL_NAME
    if dev_path.exists():
        return dev_path

    # Method 2: Installed package (skills/ alongside cobo_cli/)
    try:
        import cobo_cli

        pkg_path = Path(cobo_cli.__file__).parent.parent / "skills" / SKILL_NAME
        if pkg_path.exists():
            return pkg_path
    except ImportError:
        pass

    raise click.ClickException(
        f"Could not find {SKILL_NAME} skill in package. "
        "Please reinstall cobo-cli: pip install --force-reinstall cobo-cli"
    )


if __name__ == "__main__":
    skill()
