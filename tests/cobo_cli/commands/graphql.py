import json

import click

from cobo_cli.utils.api import make_request


@click.command(
    "graphql",
    context_settings=dict(help_option_names=["-h", "--help"]),
    help="Execute a GraphQL query against the Cobo API.",
)
@click.option(
    "-q",
    "--query",
    help="The GraphQL query string.",
    required=False,
)
@click.option(
    "-v",
    "--variables",
    help="JSON string of variables for the GraphQL query.",
    default="{}",
)
@click.option(
    "-f",
    "--file",
    help="The GraphQL query file.",
    required=False,
)
@click.option(
    "--raw",
    is_flag=True,
    help="Output the raw JSON response.",
)
@click.pass_context
def graphql(ctx: click.Context, query: str, variables: str, file: str, raw: bool):
    """Execute a GraphQL query against the Cobo API."""
    if query is None and file is None:
        raise click.MissingParameter("Missing argument 'query' or 'file'.")
    if not query:
        with open(file, "r") as f:
            query = f.read()

    try:
        # Parse the query input as JSON
        query_data = json.loads(query)
        if isinstance(query_data, dict) and "query" in query_data:
            query = query_data["query"]
        else:
            raise click.BadParameter(
                "Query must be a valid JSON string containing a 'query' key."
            )
    except json.JSONDecodeError:
        # If it's not valid JSON, assume it's a raw GraphQL query string
        pass

    try:
        variables_dict = json.loads(variables)
    except json.JSONDecodeError:
        raise click.BadParameter("Variables must be a valid JSON string.")

    payload = {"query": query, "variables": variables_dict}

    response = make_request(ctx, "POST", "/graphql", prefix="/web", json=payload)

    if raw:
        click.echo(response.text)
    else:
        try:
            formatted_response = json.dumps(response.json(), indent=2)
            click.echo_via_pager(formatted_response)
        except json.JSONDecodeError:
            click.echo(response.text)


if __name__ == "__main__":
    graphql()
