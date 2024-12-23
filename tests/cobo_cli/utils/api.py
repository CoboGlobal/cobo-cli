import json
import time
from urllib.parse import urlencode

import click
import requests
from dotenv import get_key, load_dotenv

from cobo_cli.data.auth_methods import AuthMethodType
from cobo_cli.data.context import CommandContext
from cobo_cli.utils.app import (
    app_directory_with_env_file,
    validate_manifest_and_get_app_id,
)
from cobo_cli.utils.openapi import (
    format_help,
    get_api_details,
    get_parameter_help,
    load_api_spec,
    resolve_reference,
)
from cobo_cli.utils.signer import Signer


def prepare_auth_headers(key, secret, method, path, nonce, params, body):
    if not key or not secret:
        raise click.ClickException(
            "Key or secret not found. Please run 'cobo keys generate' to generate a new key pair."
        )

    str_to_sign = f"{method.upper()}|{path}|{nonce}|{params}|{body}"
    signer = Signer(private_key=secret)
    signature = signer.sign(str_to_sign)

    return {
        "Biz-Api-Key": key,
        "Biz-Api-Nonce": str(nonce),
        "Biz-Api-Signature": signature.hex(),
    }


def make_request(ctx, method, path, prefix="/v2", auth=None, **kwargs):
    command_context: CommandContext = ctx.obj
    auth = auth or command_context.auth_method
    config_manager = command_context.config_manager
    base_url = config_manager.get_config("api_host")

    # Replace path parameters with their values
    path_params = kwargs.pop("path_params", {})
    for param, value in path_params.items():
        path = path.replace(f"{{{param}}}", value)

    path = prefix + path

    url = f"{base_url}{path}"

    headers = {}
    nonce = int(time.time() * 1000)
    params = urlencode(kwargs.get("params", {}))
    body = json.dumps(kwargs.get("json", {})) if kwargs.get("json") else ""

    if auth == AuthMethodType.APIKEY:
        key = config_manager.get_config("api_key")
        secret = config_manager.get_config("api_secret")
        headers.update(
            prepare_auth_headers(key, secret, method, path, nonce, params, body)
        )
    elif auth == AuthMethodType.ORG:
        if not app_directory_with_env_file():
            raise click.ClickException(
                "Making request with org token requires a valid app directory with .env file."
            )

        # Load environment variables
        load_dotenv()

        # Retrieve app_key from manifest and app_secret from .env
        manifest, _ = validate_manifest_and_get_app_id(ctx, require_app_id=False)
        app_key = manifest.app_key
        app_secret = get_key(".env", "APP_SECRET")
        org_token = get_key(".env", f"ORG_TOKEN_{get_key('.env', 'CURRENT_ORG_UUID')}")

        headers.update(
            prepare_auth_headers(app_key, app_secret, method, path, nonce, params, body)
        )
        if org_token:
            headers["Authorization"] = f"Bearer {org_token}"
    elif auth == AuthMethodType.USER:
        user_token = config_manager.get_config("user_access_token")
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
    elif auth == AuthMethodType.NONE:
        pass
    else:
        raise click.ClickException(f"Invalid authentication method: {auth}")

    click.echo(f"Making {method} request to {url}")

    response = requests.request(method, url, headers=headers, **kwargs)

    return response


def handle_api_request(ctx, spec, path, method, params=None):
    api_details, matched_path = get_api_details(spec, path, method)

    if api_details:
        request_params = {}
        path_params = {}

        # Extract path parameters
        spec_parts = matched_path.split("/")
        input_parts = path.split("/")
        for spec_part, input_part in zip(spec_parts, input_parts):
            if spec_part.startswith("{") and spec_part.endswith("}"):
                param_name = spec_part[1:-1]
                path_params[param_name] = input_part

        if params:
            request_params = params
        else:
            if method.lower() in ["get", "delete"]:
                parameters = api_details.get("parameters", [])
                for param in parameters:
                    if "$ref" in param:
                        param = resolve_reference(spec, param["$ref"])
                    name = param.get("name", "Unknown")
                    if (
                        name not in path_params
                    ):  # Only prompt for parameters not in the path
                        description = param.get("description", "No description")
                        required = param.get("required", False)

                        if required:
                            value = click.prompt(
                                f"{name} (REQUIRED - {description})", type=str
                            )
                            request_params[name] = value
            else:  # POST or PUT
                if "requestBody" in api_details:
                    request_body = api_details["requestBody"]
                    if "$ref" in request_body:
                        request_body = resolve_reference(spec, request_body["$ref"])
                    content = request_body.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        if "$ref" in schema:
                            schema = resolve_reference(spec, schema["$ref"])
                        required_props = schema.get("required", [])
                        for prop in required_props:
                            details = schema.get("properties", {}).get(prop, {})
                            if "$ref" in details:
                                details = resolve_reference(spec, details["$ref"])
                            description = details.get("description", "No description")

                            value = click.prompt(
                                f"{prop} (REQUIRED - {description})", type=str
                            )
                            request_params[prop] = value

        # Use matched_path instead of path, and pass path_params separately
        if method.lower() in ["get", "delete"]:
            response = make_request(
                ctx,
                method,
                matched_path,
                params=request_params,
                path_params=path_params,
            )
        else:
            response = make_request(
                ctx,
                method,
                matched_path,
                json=request_params if len(request_params.keys()) else None,
                path_params=path_params,
            )

        try:
            response_json = response.json()
            formatted_response = json.dumps(response_json, indent=2)
            click.echo_via_pager(formatted_response)
        except json.JSONDecodeError:
            click.echo(response.text)
    else:
        click.echo(f"No {method.upper()} operation found for path: {path}")


def validate_parameters(spec, path, method, params):
    api_details, matched_path = get_api_details(spec, path, method)
    if not api_details:
        return False, f"No {method.upper()} operation found for path: {path}"

    valid_params = set()
    if method.lower() in ["get", "delete"]:
        for param in api_details.get("parameters", []):
            if "$ref" in param:
                param = resolve_reference(spec, param["$ref"])
            valid_params.add(param.get("name"))
    else:  # POST or PUT
        if "requestBody" in api_details:
            request_body = api_details["requestBody"]
            if "$ref" in request_body:
                request_body = resolve_reference(spec, request_body["$ref"])
            content = request_body.get("content", {}).get("application/json", {})
            schema = content.get("schema", {})
            if "$ref" in schema:
                schema = resolve_reference(spec, schema["$ref"])
                if "discriminator" in schema:
                    property_name = schema["discriminator"]["propertyName"]
                    property_mapping = schema["discriminator"]["mapping"]
                    property_mapping_key = params[property_name]
                    schema = resolve_reference(
                        spec, property_mapping[property_mapping_key]
                    )
            valid_params = set(schema.get("properties", {}).keys())

    invalid_params = set(params.keys()) - valid_params
    if invalid_params:
        return (
            False,
            f"Invalid parameter(s): {', '.join(invalid_params)}. "
            f"Valid parameters are: {', '.join(valid_params)}",
        )

    return True, None


def list_api_operations(spec, method):
    operations = []
    for path, path_item in spec["paths"].items():
        if method.lower() in path_item:
            operations.append(path)
    return operations


def get_operation_help(spec, path, method):
    api_details, _ = get_api_details(spec, path, method)
    if api_details:
        help_text = format_help(
            f"{method.upper()} {path}", api_details, spec, is_operation=True
        )
        return help_text
    else:
        return click.style(
            f"No {method.upper()} operation found for path: {path}", fg="red"
        )


def create_api_command(method):
    @click.command(
        method,
        context_settings=dict(
            help_option_names=["-h", "--help"],
            ignore_unknown_options=True,
            allow_extra_args=True,
        ),
    )
    @click.argument("path", required=False)
    @click.option(
        "-d", "--describe", is_flag=True, help="Display operation description"
    )
    @click.option(
        "-l", "--list", is_flag=True, help="List all API operations for this method"
    )
    @click.pass_context
    def command(ctx, path, describe, list):
        """Make a {method} request to a Cobo API endpoint."""

        command_context: CommandContext = ctx.obj
        spec = (
            command_context.api_spec or load_api_spec()
        )  # Fall back to default if not provided

        if list:
            operations = list_api_operations(spec, method.upper())
            if operations:
                click.echo(f"API operations for {method.upper()}:")
                for operation in operations:
                    click.echo(f"  - {operation}")
            else:
                click.echo(f"No API operations found for {method.upper()}.")
            return

        if describe:
            if path:
                api_details, matched_path = get_api_details(spec, path, method.upper())
                if api_details:
                    params_to_describe = [
                        arg.lstrip("--") for arg in ctx.args if arg.startswith("--")
                    ]
                    if params_to_describe:
                        for param in params_to_describe:
                            error_message = get_parameter_help(
                                spec, path, method.upper(), param
                            )
                            if error_message:
                                click.echo(error_message)
                    else:
                        help_text = get_operation_help(spec, path, method.upper())
                        click.echo_via_pager(help_text)
                else:
                    click.echo(
                        click.style(
                            f"No {method.upper()} operation found for path: {path}",
                            fg="red",
                        )
                    )
            else:
                click.echo(
                    click.style(
                        "Error: Path is required to describe an operation.", fg="red"
                    )
                )
            return

        if not path:
            click.echo(
                click.style("Error: Path is required to make a request.", fg="red")
            )
            return

        params = {}
        args = ctx.args
        for i in range(0, len(args), 2):
            key = args[i].lstrip("-")
            value = args[i + 1] if i + 1 < len(args) else True
            params[key] = value

        # Validate parameters
        is_valid, error_message = validate_parameters(
            spec, path, method.upper(), params
        )
        if not is_valid:
            click.echo(f"Error: {error_message}", err=True)
            return

        handle_api_request(ctx, spec, path, method.upper(), params)

    return command
