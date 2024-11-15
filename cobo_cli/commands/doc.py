import webbrowser

import click

from cobo_cli.data.context import CommandContext
from cobo_cli.utils.api import get_operation_help, load_api_spec
from cobo_cli.utils.openapi import update_spec


@click.command(
    "doc",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Open Cobo documentation or display API operation information.",
)
@click.argument("topic_or_path", default="general")
@click.option("-u", "--update", is_flag=True, help="Update the OpenAPI specification")
@click.pass_context
def doc(ctx: click.Context, topic_or_path: str, update: bool):
    """Open Cobo documentation in the default web browser or display API operation information."""
    command_context: CommandContext = ctx.obj

    if update:
        update_spec()
        return

    base_url = "https://www.cobo.com/developers/v2/"

    url_mapping = {
        "guides": "/guides",
        "api": "/api-references/playground",
        "sdk": "/developer-tools/quickstart-python",
        "app": "/apps/introduction",
    }

    if topic_or_path.startswith("/"):
        # This is an API path, display operation information
        spec = (
            command_context.api_spec or load_api_spec()
        )  # Fall back to default if not provided
        path_info = spec["paths"].get(topic_or_path)

        if path_info:
            click.echo(
                click.style(
                    f"API Operations for {topic_or_path}:\n", fg="cyan", bold=True
                )
            )
            for method in ["get", "post", "put", "delete"]:
                if method in path_info:
                    help_text = get_operation_help(spec, topic_or_path, method.upper())
                    click.echo(help_text)
        else:
            click.echo(
                click.style(
                    f"No API operations found for path: {topic_or_path}", fg="red"
                )
            )
    elif topic_or_path in url_mapping:
        url = base_url + url_mapping[topic_or_path]
        click.echo(f"Opening {topic_or_path} documentation in your default browser...")
        webbrowser.open(url)
    else:
        click.echo(f"Unknown documentation topic or API path: {topic_or_path}")


if __name__ == "__main__":
    doc()
