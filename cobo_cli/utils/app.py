import logging
import os
import tarfile
import tempfile
from pathlib import Path

import click
import requests
from click import BadParameter

from cobo_cli.data.environments import EnvironmentType
from cobo_cli.data.manifest import Manifest
from cobo_cli.utils.code_gen import ProcessContext, TemplateCodeGen
from cobo_cli.utils.config import default_manifest_file

logger = logging.getLogger(__name__)
GITHUB_REPO_BASE_URL = "https://github.com/CoboGlobal"


def download_file(url: str, path: str) -> None:
    """
    Download a file from a given URL and save it to the specified path.
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()

    # Only create directories if the path is not a temporary file
    if not path.startswith("/var/folders") and not path.startswith("/tmp"):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)


def extract_file(file_path: str, directory: str):
    with tarfile.open(file_path, "r:gz") as tar_ref:
        root_dirs = []
        for member in tar_ref.getmembers():
            if member.isdir():
                r_dir = member.name.split("/")
                r_dir = r_dir[0]
                if r_dir not in root_dirs:
                    root_dirs.append(r_dir)
        if len(root_dirs) == 1:
            root_dir = root_dirs[0].rstrip("/")
            for member in tar_ref.getmembers():
                if member.name.rstrip("/") != root_dir and member.name.startswith(
                    root_dir + "/"
                ):
                    member.name = member.name[len(root_dir + "/") :]
                    tar_ref.extract(member, directory)
        else:
            tar_ref.extractall(directory)


def is_app_directory() -> bool:
    """
    Check if the current directory is an app directory.
    """
    return os.path.isfile(default_manifest_file)


def app_directory_with_env_file():
    if not is_app_directory():
        click.echo("Not in an app directory. No manifest.json found.")
        return False

    if not os.path.isfile(".env"):
        click.echo("No .env file found. Please login to an organization first.")
        return False

    return True


def validate_manifest_and_get_app_id(
    ctx: click.Context, require_dev_app_id: bool = True, require_app_id: bool = False
) -> tuple[Manifest, str]:
    if not is_app_directory():
        raise BadParameter(
            f"The file {default_manifest_file} does not exist. "
            "Please ensure you are running this command in a portal app directory that contains a manifest file. "
            "If you haven't created a manifest file yet, please create and update it first.",
            ctx=ctx,
        )

    env = ctx.obj.env

    try:
        manifest = Manifest.load(default_manifest_file)
    except ValueError as e:
        raise BadParameter(str(e), ctx=ctx)

    if require_dev_app_id and not manifest.dev_app_id:
        raise BadParameter(
            f"The field dev_app_id does not exist in {default_manifest_file}", ctx=ctx
        )

    if env == EnvironmentType.PRODUCTION:
        if require_app_id and not manifest.app_id:
            raise BadParameter(
                "The field app_id does not exist in manifest.json", ctx=ctx
            )
        app_id = manifest.app_id
    else:
        app_id = manifest.dev_app_id

    return manifest, app_id


def create_sub_project(
    project_dir: str,
    sub_dir: str,
    app_type: str,
    framework: str,
    wallet_type: str,
    auth: str,
):
    sub_project_dir = os.path.join(project_dir, sub_dir)
    os.makedirs(sub_project_dir, exist_ok=True)

    repo_name = f"cobo-{framework}-template"
    archive_url = f"{GITHUB_REPO_BASE_URL}/{repo_name}/archive/main.tar.gz"

    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as temp_file:
            temp_file_path = temp_file.name
            download_file(archive_url, temp_file_path)

            extract_file(temp_file_path, sub_project_dir)
    except requests.RequestException as e:
        logger.error(f"Failed to download template: {e}")
        raise click.ClickException(f"Failed to download template: {e}")
    except tarfile.TarError as e:
        logger.error(f"Failed to extract template: {e}")
        raise click.ClickException(f"Failed to extract template: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise click.ClickException(f"An unexpected error occurred: {e}")
    finally:
        # Clean up the temporary file
        if "temp_file_path" in locals():
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")

    # Call post_process after extracting the template
    post_process(sub_project_dir, app_type, wallet_type, auth)


def post_process(sub_project_dir: str, app_type: str, wallet_type: str, auth: str):
    """后处理项目文件"""
    context = ProcessContext(app_type=app_type, wallet_type=wallet_type, auth=auth)
    code_gen_file = Path(sub_project_dir) / ".code_gen.yaml"
    code_gen = TemplateCodeGen(code_gen_file)
    code_gen.process(sub_project_dir, context)
