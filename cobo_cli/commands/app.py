import logging
import os
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path
from typing import Any, Callable, Optional, Union

import click
from click import BadParameter, ParamType

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.constants import convert_wallet_type, supported_wallet_type_choices
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.manifest import Manifest, available_wallet_types
from cobo_cli.utils.api import make_request
from cobo_cli.utils.app import create_sub_project, validate_manifest_and_get_app_id
from cobo_cli.utils.code_gen import ProcessContext, TemplateCodeGen
from cobo_cli.utils.config import default_manifest_file

logger = logging.getLogger(__name__)


@click.group(
    "app",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Commands to create, run, upload, and manage Cobo applications.",
)
@click.pass_context
def app(ctx: click.Context):
    """Application management command group."""


@app.command("init", help="Create a new Cobo application project.")
@click.option(
    "-t",
    "--app-type",
    type=click.Choice(["portal", "web", "mobile", "automation"]),
    help="Type of application to create",
)
@click.option(
    "--auth",
    type=click.Choice(["apikey", "org", "user"]),
    help="Authentication mechanism for Cobo's WaaS service",
)
@click.option(
    "--wallet-type",
    type=click.Choice(supported_wallet_type_choices),
    help="Wallet type to include",
)
@click.option(
    "--mobile",
    type=click.Choice(["flutter", "react-native", "kotlin", "swift"]),
    help="Mobile development framework",
)
@click.option(
    "--web",
    type=click.Choice(["react", "nextjs", "vue", "svelte"]),
    help="Web development framework",
)
@click.option(
    "--backend",
    type=click.Choice(
        [
            "fastapi",
            "django",
            "express",
            "flask",
            "spring-boot",
            "gin",
            "laravel",
            "rails",
            "nextjs",
        ]
    ),
    help="Backend development framework",
)
@click.option(
    "-d",
    "--directory",
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    required=False,
    help="Directory to create the project in",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force overwrite the project directory if it already exists",
)
@click.pass_context
def init_app(
    ctx,
    app_type,
    auth,
    wallet_type,
    mobile,
    web,
    backend,
    directory,
    force,
):
    def prompt(
        text: str,
        type: Optional[Union[ParamType, Any]] = None,
        default: Optional[Any] = None,
        available_types: Optional[Union[ParamType, Any]] = None,
        validate_func: Optional[Callable] = None,
        error_msg_func: Optional[Callable] = None,
    ) -> str:
        def _validate_options(_validate_func: Callable, _value: str):
            if not _validate_func(_value):
                click.echo(
                    error_msg_func(_value)
                    if error_msg_func
                    else f"We don't support {_value} for now, please wait for future release version."
                )
                _value = click.prompt(
                    text,
                    type=type,
                    default=default,
                    value_proc=partial(_validate_options, _validate_func),
                )
            return _value

        def _default_validate_func(_value: str):
            return _value in available_types

        value = click.prompt(
            text,
            type=type,
            default=default,
            value_proc=partial(
                _validate_options, validate_func or _default_validate_func
            ),
        )
        return value

    # Prompt for missing information
    if not app_type:
        app_type = prompt(
            "What application are you building",
            type=click.Choice(["portal", "web", "mobile", "automation"]),
            default="portal",
            available_types=["portal", "web"],
        )

    if not auth:
        auth = click.prompt(
            "What authentication mechanism are you going to use",
            type=click.Choice(["apikey", "org", "user"]),
        )

    if not wallet_type:
        wallet_type = click.prompt(
            "What wallet type do you want to choose?",
            type=click.Choice(supported_wallet_type_choices, case_sensitive=False),
        )

    if app_type == "mobile" and not mobile:
        mobile = click.prompt(
            "Select mobile framework",
            type=click.Choice(["flutter", "react-native", "kotlin", "swift"]),
        )

    if app_type in ["web", "portal"] and not web:
        web = prompt(
            "Select web framework",
            type=click.Choice(
                [
                    "react",
                    "nextjs",
                    "vue",
                    "svelte",
                ]
            ),
            default="react",
            available_types=["react"],
        )

    if not backend:
        backend = prompt(
            "Select backend framework",
            type=click.Choice(
                [
                    "fastapi",
                    "django",
                    "express",
                    "flask",
                    "spring-boot",
                    "gin",
                    "laravel",
                    "rails",
                    "nextjs",
                ]
            ),
            default="fastapi",
            available_types=["fastapi"],
        )

    if not directory:
        directory = click.prompt(
            "Enter project directory",
            type=click.Path(file_okay=False, dir_okay=True, writable=True),
        )

    # Create project directory
    project_dir = os.path.abspath(directory)
    if os.path.exists(project_dir) and not force:
        raise click.ClickException(
            f"Directory {project_dir} already exists. To overwrite it, use the --force option."
        )
    os.makedirs(project_dir, exist_ok=True)
    wallet_type = convert_wallet_type(wallet_type)

    # Initialize project structure based on type
    if app_type == "mobile":
        create_sub_project(project_dir, "mobile", app_type, mobile, wallet_type, auth)

    elif app_type in ["web", "portal"]:
        create_sub_project(project_dir, "frontend", app_type, web, wallet_type, auth)

    create_sub_project(project_dir, "backend", app_type, backend, wallet_type, auth)

    # Create a manifest file if the app type is "portal"
    if app_type == "portal":
        manifest_file_path = os.path.join(project_dir, default_manifest_file)

        # Ask user if they want to set attributes now
        if click.confirm("Would you like to create the app manifest file now?"):
            # Collect user inputs for manifest attributes
            app_name = click.prompt("App Name", default="YourAppName")
            app_desc = click.prompt(
                "Short Description", default="Short description of your app"
            )
            app_icon_url = click.prompt(
                "App Icon URL", default="https://example.com/icon.png"
            )
            homepage_url = click.prompt("Homepage URL", default="http://localhost:5000")
            app_key = click.prompt("App Key", default="your-app-key")
            app_desc_long = click.prompt(
                "Long Description", default="A longer description of your app"
            )
            creator_name = click.prompt("Creator Name", default="Your Name")
            contact_email = click.prompt(
                "Contact Email", default="your-email@example.com"
            )
            support_site_url = click.prompt(
                "Support Site URL", default="https://example.com/support"
            )
            callback_urls = click.prompt(
                "Callback URLs (comma-separated)",
                default="https://example.com/callback",
            ).split(",")
            screen_shots = click.prompt(
                "Screenshots URLs (comma-separated)",
                default="https://example.com/screenshot_1.png,https://example.com/screenshot_2.png,"
                "https://example.com/screenshot_3.png",
            ).split(",")

            def _validate_wallet_type(_wallet_types: str):
                _wallet_types = [item for item in _wallet_types.split(",") if item]
                return all(
                    [item.strip() in available_wallet_types for item in _wallet_types]
                )

            def _error_msg_func(_user_input):
                _wallet_types = _user_input.split(",")
                _invalid_wallet_type = [
                    item
                    for item in _wallet_types
                    if item.strip() not in available_wallet_types
                ]
                return (
                    f"We don't support {_invalid_wallet_type} for now, "
                    f"supported wallet types are {available_wallet_types}."
                )

            wallet_types = prompt(
                "Supported Wallet types (comma-separated). Leave it blank to support all wallet types.",
                type=str,
                default="",
                available_types=available_wallet_types,
                validate_func=_validate_wallet_type,
                error_msg_func=_error_msg_func,
            )

            is_policy_reminded = click.prompt(
                "Notice user to set up transaction policies?(default true)",
                type=bool,
                default=True,
            )

            required_permissions = click.prompt(
                "Required Permissions (semicolon-separated)",
                default="resource:action",
            ).split(",")

            operation_approval_rules = click.prompt(
                "Operation approval rules",
                type=list[dict],
                default=[],
            )

            manifest_data = {
                "app_name": app_name,
                "app_desc": app_desc,
                "app_icon_url": app_icon_url,
                "homepage_url": homepage_url,
                "app_key": app_key,
                "app_desc_long": app_desc_long,
                "creator_name": creator_name,
                "contact_email": contact_email,
                "support_site_url": support_site_url,
                "callback_urls": callback_urls,
                "screen_shots": screen_shots,
                "wallet_types": (
                    [item.strip() for item in wallet_types.split(",")]
                    if wallet_types
                    else []
                ),
                "is_policy_reminded": is_policy_reminded,
                "required_permissions": required_permissions,
                "operation_approval_rules": operation_approval_rules,
            }
            Manifest.create_with_defaults(manifest_file_path, manifest_data)
        else:
            Manifest.create_with_defaults(manifest_file_path)

        click.echo(
            f"A new manifest file has been created at {manifest_file_path}. "
            "Please edit it to set the correct values for your app attributes."
        )

    click.echo(
        f"Successfully created Cobo application project of type {app_type} "
        f"with {auth} authentication and {wallet_type} wallet technology "
        f"in {project_dir}"
    )


@app.command(
    "run",
    help="Run a Cobo application.",
)
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

    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    env_type = command_context.env.value
    if env_type not in ["dev", "sandbox"]:
        raise BadParameter("Environment should be 'sandbox' or 'dev' to run the app")

    def process_app(_port):
        run_command = get_run_command()
        click.echo(f"Starting application on port {_port}...")
        commands = [*run_command.split(), "--port", f"{_port}", "--env", env_type]
        if iframe:
            manifest, _ = Manifest.load()
            app_uuid = manifest.dev_app_id if manifest else None
            app_uuid = app_uuid or command_context.env.default_app_id
            if app_uuid:
                url = f"{config_manager.get_config('base_url').rstrip('/')}/apps/myApps/allApps/{app_uuid}"
                commands.append("--url")
                commands.append(url)
        subprocess.run(commands, check=True)

    def get_run_command():
        if os.path.isfile("start.sh"):
            return "bash start.sh"
        if os.path.isfile("scripts/start.sh"):
            return "bash scripts/start.sh"
        else:
            raise BadParameter("No start.sh script found.")

    process_app(port)


@app.command("upload", help="Upload a Cobo application.")
@click.pass_context
def upload_app(ctx: click.Context) -> None:
    """Upload a Cobo application."""
    manifest, _ = validate_manifest_and_get_app_id(
        ctx, require_dev_app_id=False, require_app_id=False
    )

    # Check if app_key is set
    if not manifest.app_key or manifest.app_key == "your-app-key":
        click.echo("The app_key is not set in the manifest file.")
        click.echo("Please run the following command to generate an app key first:")
        click.echo("  cobo keys generate --key-type APP")
        return

    env = ctx.obj.env

    if env in [EnvironmentType.DEVELOPMENT, EnvironmentType.SANDBOX]:
        if manifest.dev_app_id:
            raise BadParameter(
                f"The field dev_app_id already exists in {default_manifest_file}",
                ctx=ctx,
            )
    elif env == EnvironmentType.PRODUCTION:
        if not manifest.dev_app_id:
            raise BadParameter(
                f"The field dev_app_id does not exist in {default_manifest_file}",
                ctx=ctx,
            )
        if manifest.app_id:
            raise BadParameter(
                f"The field app_id already exists in {default_manifest_file}",
                ctx=ctx,
            )
    else:
        raise BadParameter(f"Not supported in {env.value} environment")

    # Check if user is logged in
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    user_token = config_manager.get_config("user_access_token")

    if not user_token:
        raise click.ClickException(
            "User is not logged in. Please log in first using 'cobo login -u' command."
        )

    try:
        json_data = manifest.model_dump(mode="json", exclude_unset=True, by_alias=True)
        if ctx.obj.env == EnvironmentType.PRODUCTION:
            json_data["app_id"] = json_data["dev_app_id"]
        response = make_request(
            ctx,
            "POST",
            "/appstore/apps",
            prefix="/web/v2",
            auth=AuthMethodType.USER,
            json=json_data,
        )
        result = response.json()

        if response.status_code != 201 or not result.get("success"):
            raise Exception(
                f"App upload failed. error_message: {result.get('error_message')}, "
                f"error_id: {result.get('error_id')}"
            )

        app_id = result["result"].get("app_id")
        client_id = result["result"].get("client_id")

        if ctx.obj.env == EnvironmentType.PRODUCTION:
            manifest.app_id = app_id
            manifest.client_id = client_id
        else:
            manifest.dev_app_id = app_id
            manifest.dev_client_id = client_id

        manifest.save()
        click.echo(f"App uploaded successfully with app_id: {app_id}")
    except Exception as e:
        raise click.ClickException(str(e))


@app.command("update", help="Update a Cobo application.")
@click.pass_context
def update_app(ctx: click.Context) -> None:
    """Update a Cobo application."""
    manifest, app_id = validate_manifest_and_get_app_id(ctx)

    try:
        response = make_request(
            ctx,
            "PUT",
            f"/appstore/apps/{app_id}",
            prefix="/web/v2",
            json=manifest.model_dump(
                mode="json", exclude_unset=True, exclude={"app_id"}, by_alias=True
            ),
            auth=AuthMethodType.USER,
        )
        result = response.json()

        if response.status_code != 200 or not result.get("success"):
            raise Exception(
                f"App update failed. error_message: {result.get('error_message')}, "
                f"error_id: {result.get('error_id')}"
            )

        client_id = result["result"].get("client_id")
        if ctx.obj.env == EnvironmentType.PRODUCTION:
            manifest.client_id = client_id
        else:
            manifest.dev_client_id = client_id
        manifest.save()
        click.echo(f"App updated successfully with app_id: {app_id}")
    except Exception as e:
        raise click.ClickException(str(e))


@app.command("manifest", help="Get value from manifest file.")
@click.option(
    "-k",
    "--key",
    type=str,
    help="Specify the key to retrieve from manifest.json. If not provided, the manifest file path is shown.",
)
@click.pass_context
def get_manifest(ctx: click.Context, key: str = None) -> None:
    try:
        manifest, file_path = Manifest.load()
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)
    if not key:
        click.echo(file_path)
        return
    value = getattr(manifest, key, "")
    if not value:
        raise BadParameter(f"No {key} field in Manifest.json.")
    click.echo(value)


@app.command("status", help="Check the status of a Cobo application.")
@click.pass_context
def app_status(ctx: click.Context) -> None:
    """Check the status of a Cobo application."""
    _, app_id = validate_manifest_and_get_app_id(ctx, require_app_id=True)

    try:
        response = make_request(
            ctx,
            "GET",
            f"/appstore/apps/{app_id}/status",
            prefix="/web/v2",
            auth=AuthMethodType.USER,
        )
        result = response.json()

        if response.status_code != 200 or not result.get("success"):
            raise Exception(
                f"Check app status failed. error_message: {result.get('error_message')}, "
                f"error_id: {result.get('error_id')}"
            )

        status = result["result"].get("status")
        click.echo(f"app_id: {app_id}, status: {status}")
    except Exception as e:
        raise click.ClickException(str(e))


@app.command(
    "test-template", help="Test Cobo templating functionality on a file or directory."
)
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "-t",
    "--app-type",
    type=click.Choice(["portal", "web", "mobile", "automation"]),
    required=True,
    help="Type of application",
)
@click.option(
    "--auth",
    type=click.Choice(["apikey", "org", "user"]),
    required=True,
    help="Authentication mechanism for Cobo's WaaS",
)
@click.option(
    "--wallet-type",
    type=click.Choice(supported_wallet_type_choices),
    required=True,
    help="Wallet type to include",
)
@click.option(
    "--code-gen-file",
    type=click.Path(file_okay=True, dir_okay=False),
    required=False,
    help="Code generation rules file",
)
@click.pass_context
def test_template(ctx, path, app_type, auth, wallet_type, code_gen_file):
    """Test Cobo templating functionality on a file or directory."""
    path = Path(path)
    context = ProcessContext(
        app_type=app_type, wallet_type=convert_wallet_type(wallet_type), auth=auth
    )
    code_gen = TemplateCodeGen(code_gen_file)

    if path.is_file():
        # Process single file
        with open(path, "r") as f:
            content = f.read()
            processed_content = code_gen.process_template(content, context)
            click.echo(processed_content)
    elif path.is_dir():
        # Process directory
        temp_dir = tempfile.mkdtemp()
        try:
            # Copy directory contents to temp directory
            for item in path.glob("**/*"):
                if item.is_file():
                    dest = Path(temp_dir) / item.relative_to(path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(item.read_bytes())

            code_gen.process(temp_dir, context)
            # Print processed files
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, temp_dir)
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                        click.echo(f"\n--- {relative_path} ---")
                        click.echo(content)
                    except UnicodeDecodeError:
                        # Skip non-UTF-8 files
                        pass

        finally:
            # Clean up temp directory
            import shutil

            shutil.rmtree(temp_dir)

    else:
        click.echo(f"Error: {path} is neither a file nor a directory", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()
