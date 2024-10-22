import logging
import os
import subprocess
from typing import Optional

import click
from click import BadParameter, Path

from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.frameworks import FrameworkEnum
from cobo_cli.data.manifest import Manifest
from cobo_cli.utils.common import download_file, extract_file
from cobo_cli.utils.portal_client import PortalClient
from cobo_cli.data.context import CommandContext
from cobo_cli.managers.config_manager import default_manifest_file

logger = logging.getLogger(__name__)


@click.group(
    "app",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to create, run, publish, and manage Cobo applications.",
)
@click.pass_context
def app(ctx: click.Context):
    """Application management command group."""
    pass


@app.command("init", help="Create a new Cobo application from template.")
@click.option(
    "-f",
    "--framework",
    required=True,
    type=click.Choice([e.value for e in FrameworkEnum]),
    help=f"We support {', '.join([l.value for l in FrameworkEnum])} for now",
)
@click.option(
    "-d",
    "--directory",
    required=True,
    type=Path(readable=True, writable=True, file_okay=False, dir_okay=True),
    help="Directory which need to clone to",
)
@click.pass_context
def init_app(
    ctx: click.Context,
    framework: str,
    directory: Optional[str] = None,
) -> None:
    """Create a new Cobo application."""
    directory = directory or os.getcwd()
    if not directory.startswith("/"):
        directory = os.getcwd() + "/" + directory
    if os.path.isdir(directory) and os.listdir(directory):
        raise BadParameter("directory need to be empty", ctx=ctx)

    framework_enum = FrameworkEnum(framework)
    repo_url = getattr(framework_enum, "repo")

    click.echo(f"framework - {framework}, repo - {repo_url}")

    try:
        file_path = download_file(repo_url)
        extract_file(file_path, directory)
        os.remove(file_path)

        manifest_path = f"{directory.rstrip('/')}/{default_manifest_file}"
        if os.path.exists(manifest_path):
            user_response = click.confirm(
                "Existing manifest.json. Are you going to use current manifest.json?",
            )
            if user_response:
                click.echo(f"Create success! {directory}")
                return

        try:
            manifest = Manifest.load(manifest_path)
        except ValueError as e:
            raise BadParameter(str(e), ctx=ctx)

        manifest.framework = framework
        manifest.save(manifest_path)
        click.echo(f"Create success! {directory}")
    except Exception as e:
        logger.exception("Error creating application")
        raise click.ClickException(f"Error creating application: {str(e)}")


@app.command("run", help="Run a Cobo application.")
@click.option(
    "-p",
    "--port",
    required=False,
    type=int,
    default=5000,
    help="Port which we will listen on",
)
@click.option(
    "-i",
    "--iframe",
    is_flag=True,
    default=False,
    help="Load the current app from portal via iframe",
)
@click.pass_context
def run_app(ctx: click.Context, port: int, iframe: bool):
    """Run a Cobo application."""
    
    def get_run_command():
        click.echo("Detecting application type...")
        if os.path.isfile("main.py") and "fastapi" in open("main.py").read():
            click.echo("FastAPI application detected.")
            # FastAPI setup
            venv_dir = ".venv"
            if not os.path.exists(venv_dir):
                click.echo("Creating virtual environment...")
                subprocess.run(["python", "-m", "venv", venv_dir], check=True)
            
            click.echo("Activating virtual environment...")
            venv_python = os.path.join(venv_dir, "bin", "python")
            
            # Check if requirements are installed
            if not os.path.exists(os.path.join(venv_dir, "lib")) or not any(
                os.path.exists(os.path.join(root, "fastapi"))
                for root, _, _ in os.walk(os.path.join(venv_dir, "lib"))
            ):
                click.echo("Installing dependencies...")
                subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            else:
                click.echo("Dependencies already installed.")
            
            
            # Use the virtual environment's Python to run uvicorn
            return f"{venv_python} -m uvicorn main:app --reload"
        elif os.path.isfile("package.json") and "next" in open("package.json").read():
            click.echo("Next.js application detected.")
            # Next.js setup
            if not os.path.exists("node_modules"):
                click.echo("Installing dependencies...")
                subprocess.run(["npm", "install"], check=True)
            else:
                click.echo("Dependencies already installed.")
            
            return "npm run dev"
        else:
            raise BadParameter("Unsupported application type. Only 'fastapi' and 'nextjs' are supported.", ctx=ctx)

    run_command = get_run_command()

    # Always start the local web server
    subprocess_args = run_command.split(" ")
    if port is not None:
        subprocess_args = [*subprocess_args, "--port", f"{port}"]
    click.echo(f"Starting application on port {port}...")
    subprocess.run(subprocess_args, check=True)

    # If iframe flag is true, load the app via iframe
    if iframe:
        if not os.path.isfile(f"./{default_manifest_file}"):
            raise BadParameter(
                f"The file {default_manifest_file} does not exist. please create and update it first.",
                ctx=ctx,
            )
        try:
            manifest = Manifest.load()
        except ValueError as e:
            raise BadParameter(str(e), ctx=ctx)

        app_uuid = manifest.dev_app_id or ctx.obj.env.default_app_id
        if not app_uuid:
            raise BadParameter("Invalid dev_app_id in manifest.json.", ctx=ctx)

        command_context: CommandContext = ctx.obj
        client = PortalClient(ctx=ctx)
        app_resp = client.get_app(app_uuid)
        if not app_resp or not app_resp.success:
            raise BadParameter(
                app_resp.exception.errorMessage or "Invalid dev_app_id in manifest.json.",
                ctx=ctx,
            )

        url = (
            command_context.config_manager.get_config("base_url").rstrip("/")
            + f"/apps/myApps/allApps/{app_uuid}"
        )
        click.echo(f"Open {url} in browser")
        click.launch(url)


@app.command("publish", help="Publish a Cobo application.")
@click.pass_context
def publish_app(ctx: click.Context) -> None:
    """Publish a Cobo application."""
    if not os.path.exists(default_manifest_file):
        raise BadParameter(
            f"The file {default_manifest_file} does not exist. please create and update it first.",
            ctx=ctx,
        )

    try:
        manifest = Manifest.load()
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    env = ctx.obj.env

    try:
        manifest.validate_required_fields(default_manifest_file, env)
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    if env in [
        EnvironmentType.DEVELOPMENT,
        EnvironmentType.SANDBOX,
    ]:
        if manifest.dev_app_id:
            raise BadParameter(
                f"The field dev_app_id already exists in {default_manifest_file}",
                ctx=ctx,
            )
    elif env == EnvironmentType.PRODUCTION:
        if not manifest.dev_app_id:
            raise BadParameter(
                f"The field dev_app_id is not exists in {default_manifest_file}",
                ctx=ctx,
            )
        if manifest.app_id:
            raise BadParameter(
                f"The field app_id already exists in {default_manifest_file}",
                ctx=ctx,
            )
    else:
        raise BadParameter(f"Not supported in {env.value} environment")

    client = PortalClient(ctx=ctx)
    response = client.publish_app(manifest.to_dict())
    if not response.result:
        raise Exception(
            f"App publish failed. error_message: {response.exception.errorMessage}, error_id: {response.exception.errorId}"
        )

    app_id = response.result.get("app_id")
    client_id = response.result.get("client_id")
    if env == EnvironmentType.PRODUCTION:
        manifest.app_id = app_id
        manifest.client_id = client_id
    else:
        manifest.dev_app_id = app_id
        manifest.dev_client_id = client_id

    manifest.save()
    click.echo(f"App published successfully with app_id: {app_id}")


@app.command("update", help="Update a Cobo application.")
@click.pass_context
def app_update(ctx: click.Context) -> None:
    """Update a Cobo application."""
    if not os.path.exists(default_manifest_file):
        raise BadParameter(
            f"The file {default_manifest_file} does not exist. please create and update it first.",
            ctx=ctx,
        )
    env = ctx.obj.env

    try:
        manifest = Manifest.load()
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    try:
        manifest.validate_required_fields(default_manifest_file, env)
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    if not manifest.dev_app_id:
        raise BadParameter(
            f"The field dev_app_id does not exists in {default_manifest_file}", ctx=ctx
        )

    app_id = manifest.dev_app_id

    if env == EnvironmentType.PRODUCTION:
        if not manifest.app_id:
            raise BadParameter(
                "The field app_id does not exists in manifest.json", ctx=ctx
            )
        app_id = manifest.app_id

    client = PortalClient(ctx=ctx)

    response = client.update_app(app_id, manifest.to_dict())
    if not response.result:
        raise Exception(
            f"App update failed. error_message: {response.exception.errorMessage}, error_id: {response.exception.errorId}"
        )

    client_id = response.result.get("client_id")
    if env == EnvironmentType.PRODUCTION:
        manifest.client_id = client_id
    else:
        manifest.dev_client_id = client_id
    manifest.save()
    click.echo(f"App updated successfully with app_id: {app_id}")


@app.command("status", help="Check the status of a Cobo application.")
@click.pass_context
def app_status(ctx: click.Context) -> None:
    """Check the status of a Cobo application."""
    if not os.path.exists(default_manifest_file):
        raise BadParameter(
            f"The file {default_manifest_file} does not exist. please create and update it first.",
            ctx=ctx,
        )
    env = ctx.obj.env

    try:
        manifest = Manifest.load()
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    if not manifest.dev_app_id:
        raise BadParameter(
            f"The field dev_app_id does not exists in {default_manifest_file}", ctx=ctx
        )

    app_uuid = manifest.dev_app_id

    if env == EnvironmentType.PRODUCTION:
        app_uuid = manifest.app_id

    if not app_uuid:
        raise BadParameter(
            f"The field app_id does not exists in {default_manifest_file}", ctx=ctx
        )

    client = PortalClient(ctx=ctx)
    response = client.get_status(app_uuid=app_uuid)
    if not response.result:
        raise Exception(
            f"Check app status failed. error_message: {response.exception.errorMessage}, error_id: {response.exception.errorId}"
        )

    status = response.result.get("status")

    click.echo(f"app_id: {app_uuid}, status: {status}")


if __name__ == "__main__":
    app()
