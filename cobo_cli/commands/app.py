import logging
import os
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path
from typing import Any, List, Optional, Union

import click
from click import BadParameter, ParamType
from dotenv import get_key, set_key

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.manifest import Manifest
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
    help="Authentication mechanism for Cobo's WaaS",
)
@click.option(
    "--wallet-type",
    type=click.Choice(
        [
            "custodial-asset",
            "custodial-web3",
            "mpc-org-controlled",
            "mpc-user-controlled",
            "smart-contract",
            "exchange",
        ]
    ),
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
    ) -> str:
        def _validate_options(types: List[str], _value: str):
            if _value not in types:
                click.echo(
                    f"We don't support {_value} for now, please wait for future release version."
                )
                _value = click.prompt(
                    text,
                    type=type,
                    default=default,
                    value_proc=partial(_validate_options, available_types),
                )
            return _value

        value = click.prompt(
            text,
            type=type,
            default=default,
            value_proc=partial(_validate_options, available_types),
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
        wallet_choices = [
            "custodial-asset",
            "custodial-web3",
            "mpc-org-controlled",
            "mpc-user-controlled",
            "smart-contract",
            "exchange",
        ]
        wallet_type = click.prompt(
            "What Wallet Technology do you want to use?",
            type=click.Choice(wallet_choices, case_sensitive=False),
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
            homepage_url = click.prompt("Homepage URL", default="https://example.com")
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
            required_permissions = click.prompt(
                "Required Permissions (semicolon-separated)",
                default="mpc_organization_controlled_wallet:stake,custodial_asset_wallet:withdraw",
            ).split(",")

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
                "required_permissions": required_permissions,
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
    help="Run a Cobo application(We don't support 'cobo app run' command for now).",
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
@click.option(
    "--manifest-path",
    type=click.Path(file_okay=True),
    required=False,
    help="Manifest file to load",
)
@click.pass_context
def run_app(ctx: click.Context, port: int, iframe: bool, manifest_path: click.Path):
    """Run a Cobo application."""
    click.echo("Not supported yet.Will support in future versions.")
    return

    def detect_framework():
        if is_fastapi():
            click.echo("FastAPI application detected.")
            return "fastapi"
        elif is_react():
            click.echo("React application detected.")
            return "react"
        raise click.ClickException(
            "Unsupported framework detected. Please select a supported framework."
        )

    def is_fastapi():
        """Check if the application is FastAPI by file structure."""
        return any(
            os.path.isfile(path) and "fastapi" in open(path).read()
            for path in ["main.py", "app/main.py"]
        )

    def is_react():
        return os.path.isfile("package.json") and "react" in open("package.json").read()

    def fastapi_setup(_config_manager, _env_type):
        api_key = _config_manager.get_config("api_key")
        api_secret = _config_manager.get_config("api_secret")
        if not api_key or not api_secret:
            raise click.ClickException(
                f"API key and secret required for {_env_type}. Generate with 'cobo keys generate --key-type API'"
            )
        set_key(".env", "COBO_API_KEY", api_key)
        set_key(".env", "COBO_API_SECRET", api_secret)
        set_key(".env", "COBO_ENV", _env_type)

    def react_setup(_ctx, _command_context, _manifest_path) -> str:
        manifest = load_manifest(_ctx, _manifest_path)
        _app_uuid = manifest.dev_app_id or _ctx.obj.env.default_app_id
        if not manifest.app_key or manifest.app_key == "your-app-key":
            raise BadParameter(
                "The app_key is missing in manifest file. "
                "Please generate a new key with 'cobo keys generate --key-type APP'"
            )

        set_key(".env", "REACT_APP_PUBLIC_KEY", manifest.app_key)
        set_key(".env", "REACT_APP_APPID", _app_uuid)
        env_app_secret = get_key(".env", "APP_SECRET") or get_key(
            ".env", "REACT_APP_PUBLIC_SECRET"
        )
        if not env_app_secret or env_app_secret == "your-app-secret":
            click.echo(
                "APP_SECRET not found in .env file. Please fill the REACT_APP_PUBLIC_SECRET field manually."
            )
        set_key(".env", "REACT_APP_PUBLIC_SECRET", env_app_secret or "your-app-secret")
        return _app_uuid

    def load_manifest(_ctx, _manifest_path):
        path = resolve_manifest_path(_manifest_path)
        if not path:
            raise BadParameter(
                "Manifest file not found. Please create or specify the correct path",
                ctx=ctx,
            )
        try:
            return Manifest.load(path)
        except ValueError as e:
            raise BadParameter(str(e), ctx=_ctx)

    def resolve_manifest_path(_manifest_path):
        if _manifest_path and os.path.isfile(_manifest_path.resolve_path):
            return _manifest_path.resolve_path
        for default_path in [
            f"./{default_manifest_file}",
            f"../{default_manifest_file}",
        ]:
            if os.path.isfile(default_path):
                return default_path
        return None

    def open_app_in_browser(_app_uuid, _command_context):
        url = f"{_command_context.config_manager.get_config('base_url').rstrip('/')}/apps/myApps/allApps/{_app_uuid}"
        click.echo(f"Open {url} in browser")
        click.launch(url)

    def process_app(_framework, _port):
        run_command = get_run_command(_framework)
        click.echo(f"Starting application on port {_port}...")
        subprocess.run([*run_command.split(), "--port", str(_port)], check=True)

    def get_run_command(_framework):
        click.echo("Detecting application type...")
        if os.path.isfile("start.sh"):
            return "sh start.sh"
        elif _framework == "fastapi":
            return get_fastapi_run_command()
        elif _framework == "react":
            install_npm_dependencies()
            return "npm run start"
        else:
            raise BadParameter(
                "Unsupported application type. Only 'fastapi' and 'react' are supported."
            )

    def get_fastapi_run_command():
        """Prepare the command for running FastAPI with Uvicorn, using the current virtual environment if available."""
        main_py_path = find_main_py_path()
        if not is_in_virtualenv():
            setup_virtual_environment()
        else:
            if click.confirm(
                "Would you like to use current virtual environment to install dependencies?"
            ):
                click.echo("Using the current virtual environment.")
                install_dependencies(sys.executable)
            else:
                setup_virtual_environment()
        os.chdir(main_py_path)
        return f"{sys.executable} -m uvicorn main:app --reload"

    def find_main_py_path():
        """Identify and return the directory containing main.py for FastAPI."""
        for path in ["./", "./app"]:
            if os.path.isfile(os.path.join(path, "main.py")):
                return path
        raise FileNotFoundError(
            "main.py not found. Ensure that FastAPI's entry point is main.py or adjust the script accordingly."
        )

    def is_in_virtualenv():
        """Check if the current environment is a virtual environment."""
        return hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        )

    def setup_virtual_environment():
        """Create a virtual environment only if one is not already active, and install dependencies."""
        if not os.path.exists("venv"):
            click.echo("Creating virtual environment...")
            subprocess.run(["python", "-m", "venv", "venv"], check=True)
            venv_python = os.path.join("venv", "bin", "python")
            install_dependencies(venv_python)
        else:
            install_dependencies(sys.executable)

    def install_dependencies(python_executable):
        """Install dependencies using the specified Python executable."""
        click.echo("Installing dependencies...")
        subprocess.run(
            [python_executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
        )

    def install_npm_dependencies():
        click.echo("Installing npm dependencies...")
        subprocess.run(["npm", "install"], check=True)

    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
    env_type = config_manager.get_config("environment")

    if env_type not in ["dev", "sandbox"]:
        raise BadParameter("Environment should be 'sandbox' or 'dev' to run the app")
    framework = detect_framework()
    if framework == "fastapi":
        fastapi_setup(config_manager, env_type)
        process_app(framework, port)

    if framework == "react" and iframe:
        app_uuid = react_setup(ctx, command_context, manifest_path)
        open_app_in_browser(app_uuid, command_context)
        os.environ["BROWSER"] = "none"
        process_app(framework, port)
    elif framework == "react":
        os.environ["BROWSER"] = "1"
        process_app(framework, port)


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
            "User is not logged in. Please login first using 'cobo login -u' command."
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
    type=click.Choice(
        [
            "custodial-asset",
            "custodial-web3",
            "mpc-org-controlled",
            "mpc-user-controlled",
            "smart-contract",
            "exchange",
        ]
    ),
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
    context = ProcessContext(app_type=app_type, wallet_type=wallet_type, auth=auth)
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
