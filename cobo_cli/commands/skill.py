import shutil
from pathlib import Path
from typing import Dict, List

import click

# Supported AI coding agents and their skill directory names
AGENT_SKILL_DIRS: Dict[str, str] = {
    "claude": ".claude",
    "cursor": ".cursor",
    "codex": ".agents",
}

AGENT_DISPLAY_NAMES: Dict[str, str] = {
    "claude": "Claude Code",
    "cursor": "Cursor",
    "codex": "Codex",
}

DEFAULT_SKILL = "cobo-waas"


class SkillChoice(click.ParamType):
    """Lazy skill choice that defers filesystem scanning to parse time."""

    name = "skill"

    def convert(self, value, param, ctx):
        available = _list_available_skills()
        if value not in available:
            self.fail(
                f"'{value}' is not one of: {', '.join(available)}",
                param,
                ctx,
            )
        return value

    def get_metavar(self, param):
        return "NAME"


SKILL_TYPE = SkillChoice()


def _list_available_skills() -> List[str]:
    """Scan all skills/ directories to find available skill names."""
    skills: set = set()
    for base in _skill_search_roots():
        if base.is_dir():
            skills.update(
                d.name
                for d in base.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists()
            )
    return sorted(skills) if skills else [DEFAULT_SKILL]


def _skill_search_roots() -> List[Path]:
    """Return candidate roots that may contain a skills/ directory."""
    roots = [Path(__file__).parent.parent.parent / "skills"]
    try:
        import cobo_cli

        roots.append(Path(cobo_cli.__file__).parent.parent / "skills")
    except ImportError:
        pass
    return list(set(roots))


def _get_skill_path(agent: str, scope: str, skill_name: str) -> Path:
    agent_dir = AGENT_SKILL_DIRS[agent]
    base = Path.home() if scope == "global" else Path.cwd()
    return base / agent_dir / "skills" / skill_name


def _get_package_skill_path(skill_name: str) -> Path:
    """Locate a skill's source directory from the package or dev tree."""
    for root in _skill_search_roots():
        candidate = root / skill_name
        if candidate.exists() and (candidate / "SKILL.md").exists():
            return candidate

    available_skills = _list_available_skills()
    raise click.ClickException(
        f"Skill '{skill_name}' not found. Available: {', '.join(available_skills)}"
    )


def _resolve_agents(agent: str) -> List[str]:
    if agent == "all":
        return list(AGENT_SKILL_DIRS.keys())
    return [agent]


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
@click.argument("agent", type=click.Choice(["claude", "cursor", "codex", "all"]))
@click.option(
    "--skill",
    "skill_name",
    type=SKILL_TYPE,
    default=DEFAULT_SKILL,
    metavar="NAME",
    help=f"Skill to install (default: {DEFAULT_SKILL}). Run 'cobo skill list' to see options.",
)
@click.option(
    "-s",
    "--scope",
    type=click.Choice(["global", "local"]),
    default="global",
    help="Installation scope: 'global' (~/.<agent>/skills) or 'local' (./<agent>/skills in current project)",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite existing skill")
def install(agent: str, skill_name: str, scope: str, force: bool):
    """Install a skill for an AI coding agent.

    AGENT can be: claude, cursor, or all

    \b
    Examples:
      cobo skill install claude                          # Install cobo-waas globally
      cobo skill install cursor --skill cobo-payment     # Install cobo-payment for Cursor
      cobo skill install claude --scope local            # Install in current project
      cobo skill install all                             # Install cobo-waas for all agents
    """
    skill_src = _get_package_skill_path(skill_name)
    scope_label = "global" if scope == "global" else "project"

    for agent_name in _resolve_agents(agent):
        target = _get_skill_path(agent_name, scope, skill_name)
        display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)

        if target.exists() and not force:
            click.echo(f"Skill already exists at {target}. Use --force to overwrite.")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)

        shutil.copytree(skill_src, target)
        click.echo(f"Installed {skill_name} ({scope_label}) for {display_name}")
        click.echo(f"  Path: {target}")


@skill.command("list")
def list_skills():
    """List available skills."""
    available_skills = _list_available_skills()
    click.echo("Available skills:\n")
    for name in available_skills:
        click.echo(f"- {name}")
    click.echo("")
    click.echo("Supported agents: " + ", ".join(AGENT_SKILL_DIRS.keys()))
    click.echo("")
    click.echo("Usage:")
    click.echo(
        "  cobo skill install claude                          # Install default skill globally"
    )
    click.echo(
        "  cobo skill install cursor --skill cobo-payment     # Install specific skill"
    )
    click.echo(
        "  cobo skill install claude --scope local            # Install in current project"
    )
    click.echo(
        "  cobo skill install all                             # Install for all agents"
    )


@skill.command("remove")
@click.argument("agent", type=click.Choice(["claude", "cursor", "codex", "all"]))
@click.option(
    "--skill",
    "skill_name",
    type=SKILL_TYPE,
    default=DEFAULT_SKILL,
    metavar="NAME",
    help=f"Skill to remove (default: {DEFAULT_SKILL}).",
)
@click.option(
    "-s",
    "--scope",
    type=click.Choice(["global", "local", "all"]),
    default="all",
    help="Which installation to remove: 'global', 'local', or 'all' (default)",
)
def remove(agent: str, skill_name: str, scope: str):
    """Remove installed skill from an AI coding agent.

    AGENT can be: claude, cursor, or all

    \b
    Examples:
      cobo skill remove claude                          # Remove cobo-waas from Claude
      cobo skill remove cursor --skill cobo-payment     # Remove cobo-payment from Cursor
      cobo skill remove all                             # Remove cobo-waas from all agents
    """
    scopes_to_check = ["global", "local"] if scope == "all" else [scope]

    for agent_name in _resolve_agents(agent):
        display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
        removed_any = False

        for s in scopes_to_check:
            target = _get_skill_path(agent_name, s, skill_name)
            if target.exists():
                shutil.rmtree(target)
                click.echo(f"Removed {skill_name} ({s}) from {display_name}")
                removed_any = True

        if not removed_any:
            click.echo(f"No {skill_name} skill installed for {display_name}")


@skill.command("status")
@click.option(
    "--skill",
    "skill_name",
    type=SKILL_TYPE,
    default=None,
    metavar="NAME",
    help="Show status for one skill only. Default: show all available skills.",
)
def status(skill_name: str):
    """Show skill installation status."""
    skills_to_show = [skill_name] if skill_name else _list_available_skills()

    click.echo("Skill installation status:")
    click.echo("")

    for sn in skills_to_show:
        click.echo(f"  [{sn}]")
        for agent_name in AGENT_SKILL_DIRS.keys():
            display_name = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
            click.echo(f"    {display_name}:")

            for scope in ("global", "local"):
                path = _get_skill_path(agent_name, scope, sn)
                if path.exists():
                    click.echo(f"      {scope.capitalize():6s}: Installed  ({path})")
                else:
                    click.echo(f"      {scope.capitalize():6s}: Not installed")

        click.echo("")


if __name__ == "__main__":
    skill()
