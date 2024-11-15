import os
import time

import click
import requests
import yaml

from cobo_cli.utils.config import get_config_path


def update_spec():
    url = "https://raw.githubusercontent.com/CoboGlobal/developer-site/master/v2/cobo_waas2_openapi_spec/dev_openapi.yaml"  # noqa: E501
    config_dir = get_config_path()
    spec_file = os.path.join(config_dir, "openapi.yaml")

    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(spec_file, "wb") as f:
            f.write(response.content)
        click.echo("OpenAPI specification file downloaded successfully.")
    except requests.RequestException as e:
        click.echo(f"Failed to download OpenAPI specification file: {e}")


def load_api_spec(custom_spec_path=None):
    def is_spec_outdated(file_path):
        # Check if the file is older than one week
        one_week_ago = time.time() - 7 * 24 * 60 * 60
        return os.path.getmtime(file_path) < one_week_ago

    if custom_spec_path:
        if not os.path.exists(custom_spec_path):
            raise click.ClickException(
                f"Custom OpenAPI specification file not found: {custom_spec_path}"
            )
        spec_file = custom_spec_path
    else:
        config_dir = get_config_path()
        spec_file = os.path.join(config_dir, "openapi.yaml")
        if not os.path.exists(spec_file) or is_spec_outdated(spec_file):
            click.echo(
                "OpenAPI specification file not found or outdated. Downloading..."
            )
            update_spec()

    try:
        with open(spec_file, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise click.ClickException(f"Failed to open OpenAPI specification file: {e}")


def get_api_details(spec, path, method):
    if not isinstance(spec, dict) or "paths" not in spec:
        raise click.ClickException(
            "Invalid API specification format. Please ensure the OpenAPI spec is correctly loaded."
        )

    matched_path = None
    for spec_path, operations in spec["paths"].items():
        if match_path(spec_path, path):
            matched_path = spec_path
            if method.lower() in operations:
                details = operations[method.lower()]
                # Resolve any $ref in the operation details
                if "requestBody" in details and "$ref" in details["requestBody"]:
                    details["requestBody"] = resolve_reference(
                        spec, details["requestBody"]["$ref"]
                    )
                if "parameters" in details:
                    details["parameters"] = [
                        (
                            resolve_reference(spec, param["$ref"])
                            if "$ref" in param
                            else param
                        )
                        for param in details["parameters"]
                    ]
                return details, spec_path

    if matched_path is None:
        raise click.ClickException(
            f"The path '{path}' is not defined in the OpenAPI specification."
        )
    else:
        raise click.ClickException(
            f"No {method.upper()} operation found for path: {path}"
        )


def match_path(spec_path, input_path):
    spec_parts = spec_path.split("/")
    input_parts = input_path.split("/")

    if len(spec_parts) != len(input_parts):
        return False

    for spec_part, input_part in zip(spec_parts, input_parts):
        if spec_part.startswith("{") and spec_part.endswith("}"):
            continue  # This is a path parameter, so it matches any value
        if spec_part != input_part:
            return False

    return True


def resolve_reference(spec, ref):
    if not isinstance(ref, str):
        return ref

    parts = ref.split("/")
    current = spec
    for part in parts[1:]:  # Skip the first '#' part
        if part not in current:
            raise ValueError(f"Unable to resolve reference: {ref}")
        current = current[part]

    # Handle nested references
    while isinstance(current, dict) and "$ref" in current:
        current = resolve_reference(spec, current["$ref"])

    return current


def merge_all_of(schema, spec):
    if "allOf" in schema:
        merged_schema = {}
        for sub_schema in schema["allOf"]:
            resolved_sub_schema = (
                resolve_reference(spec, sub_schema["$ref"])
                if "$ref" in sub_schema
                else sub_schema
            )
            merged_schema.update(resolved_sub_schema)
        return merged_schema
    return schema


def get_discriminator_value(sub_schema, spec):
    # Check if title is present
    if "title" in sub_schema:
        return sub_schema["title"]

    # Check if description is present
    if "description" in sub_schema:
        return sub_schema["description"]

    # Check if allOf is present and resolve references
    if "allOf" in sub_schema:
        for ref in sub_schema["allOf"]:
            resolved_ref = (
                resolve_reference(spec, ref["$ref"]) if "$ref" in ref else ref
            )
            if "title" in resolved_ref:
                return resolved_ref["title"]
            if "description" in resolved_ref:
                return resolved_ref["description"]

    return "Unknown discriminator value"


def format_parameter_help(param_name, param_details, spec):
    help_text = "  "  # Start with 2 spaces indentation
    help_text += click.style(f"{param_name}", fg="cyan", bold=True)
    if param_details.get("required", False):
        help_text += click.style(" (Required)", fg="red", bold=True)
    if "example" in param_details:
        help_text += f" - Example: {param_details['example']}"
    help_text += "\n"

    description = param_details.get("description", "No description available")
    # Remove empty lines and add indentation
    description_lines = [
        line.strip() for line in description.split("\n") if line.strip()
    ]
    help_text += (
        "    "
        + click.style("Description: ", fg="yellow", bold=True)
        + f"{description_lines[0]}\n"
    )
    for line in description_lines[1:]:
        help_text += "    " + f"{line}\n"

    if "enum" in param_details:
        help_text += (
            "    " + click.style("Possible values:", fg="yellow", bold=True) + "\n"
        )
        for value in param_details["enum"]:
            help_text += f"      - {value}\n"

    # Handle array type
    if param_details.get("type") == "array":
        items = param_details.get("items", {})
        name = ""
        if "$ref" in items:
            ref = items["$ref"]
            items = resolve_reference(spec, ref)
            # Extract the name from the reference path
            name = ref.split("/")[-1]
        help_text += (
            "    "
            + click.style(
                f"Array of {name} - {items.get('description', 'No description available')}",
                fg="yellow",
                bold=True,
            )
            + "\n"
        )
        if "properties" in items:
            for prop, prop_details in items["properties"].items():
                if "$ref" in prop_details:
                    prop_details = resolve_reference(spec, prop_details["$ref"])
                help_text += "        - " + click.style(f"{prop}", fg="cyan") + " - "
                help_text += (
                    f"{prop_details.get('description', 'No description available')}\n"
                )

    return help_text


def format_oneOf_schema(discriminator, schema, spec, param_name=None):
    help_text = ""

    for sub_schema in schema["oneOf"]:
        sub_schema = resolve_reference(spec, sub_schema["$ref"])
        discriminator_value = get_discriminator_value(sub_schema, spec)
        sub_schema = merge_all_of(sub_schema, spec)
        help_text += "\n  For "
        help_text += click.style(
            f"{discriminator} = {discriminator_value}", fg="green", bold=True
        )
        help_text += ":\n"
        properties = sub_schema.get("properties", {})
        required_props = sub_schema.get("required", [])

        if param_name is None:
            for prop, prop_details in properties.items():
                if "$ref" in prop_details:
                    prop_details = resolve_reference(spec, prop_details["$ref"])
                prop_details["required"] = prop in required_props
                help_text += format_parameter_help(prop, prop_details, spec)
                help_text += "\n"  # Add an empty line after each parameter
        elif param_name in properties:
            help_text += format_parameter_help(param_name, properties[param_name], spec)

        help_text += "\n"

    return help_text


def format_help(name, details, spec, is_operation=False):
    help_text = click.style(f"{name}", fg="cyan", bold=True) + "\n"

    description = details.get("description", "No description available")
    # Remove empty lines and add indentation
    description_lines = [
        line.strip() for line in description.split("\n") if line.strip()
    ]
    help_text += (
        click.style("Description: ", fg="yellow", bold=True)
        + f"{description_lines[0]}\n"
    )
    for line in description_lines[1:]:
        help_text += f"{line}\n"

    if is_operation:
        # Handle URL parameters
        parameters = details.get("parameters", [])
        if parameters:
            help_text += (
                "\n" + click.style("URL Parameters:", fg="yellow", bold=True) + "\n"
            )
            for param in parameters:
                if "$ref" in param:
                    param = resolve_reference(spec, param["$ref"])
                param_name = param.get("name", "Unknown")
                help_text += format_parameter_help(param_name, param, spec)
                help_text += "\n"  # Add an empty line after each parameter

        # Handle request body
        if "requestBody" in details:
            help_text += (
                "\n" + click.style("Request Body:", fg="yellow", bold=True) + "\n"
            )
            request_body = details["requestBody"]
            content = request_body.get("content", {}).get("application/json", {})
            schema = content.get("schema", {})
            if "$ref" in schema:
                schema = resolve_reference(spec, schema["$ref"])

            if "oneOf" in schema:
                discriminator = schema.get("discriminator", {}).get(
                    "propertyName", "unknown discriminator"
                )
                help_text += (
                    f"  This request body can have different structures "
                    f"based on the '{discriminator}':\n"
                )
                help_text += format_oneOf_schema(discriminator, schema, spec)
            else:
                properties = schema.get("properties", {})
                required_props = schema.get("required", [])
                for prop, prop_details in properties.items():
                    if "$ref" in prop_details:
                        prop_details = resolve_reference(spec, prop_details["$ref"])
                    prop_details["required"] = prop in required_props
                    help_text += format_parameter_help(prop, prop_details, spec)
                    help_text += "\n"  # Add an empty line after each parameter

        # Add Response section
        if "responses" in details:
            help_text += "\n" + click.style("Responses:", fg="yellow", bold=True) + "\n"
            for status_code, response_details in details["responses"].items():
                if "$ref" in response_details:
                    response_details = resolve_reference(spec, response_details["$ref"])

                help_text += f"  {click.style(status_code, fg='green', bold=True)}:\n"
                description = response_details.get(
                    "description", "No description available"
                )
                help_text += f"    {description}\n"

                if "content" in response_details:
                    content = response_details["content"].get("application/json", {})
                    schema = content.get("schema", {})
                    if "$ref" in schema:
                        schema = resolve_reference(spec, schema["$ref"])

                    if "properties" in schema:
                        help_text += (
                            "    " + click.style("Response body:", fg="cyan") + "\n"
                        )
                        for prop, prop_details in schema["properties"].items():
                            if "$ref" in prop_details:
                                prop_details = resolve_reference(
                                    spec, prop_details["$ref"]
                                )
                            prop_details["required"] = prop in schema.get(
                                "required", []
                            )
                            help_text += "    " + format_parameter_help(
                                prop, prop_details, spec
                            )
                    elif "items" in schema:
                        help_text += (
                            "    "
                            + click.style("Response body (array):", fg="cyan")
                            + "\n"
                        )
                        item_schema = schema["items"]
                        if "$ref" in item_schema:
                            item_schema = resolve_reference(spec, item_schema["$ref"])
                        if "properties" in item_schema:
                            for prop, prop_details in item_schema["properties"].items():
                                if "$ref" in prop_details:
                                    prop_details = resolve_reference(
                                        spec, prop_details["$ref"]
                                    )
                                help_text += "    " + format_parameter_help(
                                    prop, prop_details, spec
                                )
                help_text += "\n"  # Add an empty line after each response

    return help_text


def get_parameter_help(spec, path, method, param_name):
    api_details, matched_path = get_api_details(spec, path, method)
    if not api_details:
        return click.style(
            f"No {method.upper()} operation found for path: {path}", fg="red"
        )

    parameters = api_details.get("parameters", [])
    for param in parameters:
        if "$ref" in param:
            param = resolve_reference(spec, param["$ref"])
        if param.get("name") == param_name:
            help_text = format_parameter_help(param_name, param, spec)
            click.echo_via_pager(help_text)  # Use echo_via_pager for paginated output
            return

    if method.lower() in ["post", "put"]:
        request_body = api_details.get("requestBody", {})
        if "$ref" in request_body:
            request_body = resolve_reference(spec, request_body["$ref"])
        content = request_body.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})
        if "$ref" in schema:
            schema = resolve_reference(spec, schema["$ref"])

        if "oneOf" in schema:
            discriminator = schema.get("discriminator", {}).get(
                "propertyName", "unknown discriminator"
            )
            help_text = format_oneOf_schema(discriminator, schema, spec, param_name)
            click.echo_via_pager(help_text)
            return
        else:
            properties = schema.get("properties", {})
            if param_name in properties:
                help_text = format_parameter_help(
                    param_name, properties[param_name], spec
                )
                click.echo_via_pager(
                    help_text
                )  # Use echo_via_pager for paginated output
                return

    return click.style(
        f"Parameter '{param_name}' not found for {method.upper()} {path}", fg="red"
    )
