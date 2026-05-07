# Cobo CLI

Cobo Command Line Interface (CLI) is a powerful developer tool designed to help you build, test, and manage your integration with [Cobo Wallet-as-a-Service (WaaS) 2.0](https://www.cobo.com/developers/v2/guides/overview/introduction) directly from the command line.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Commands](#commands)
- [Development](#development)
- [License](#license)

## Installation

To install Cobo CLI, you can use `pip` with the following command:

```bash
pip install cobo-cli
```

Ensure that you have Python 3.9 or newer installed.

Or you can install Cobo CLI via homebrew:

```bash
brew install cobo-cli
```

## Usage

To use Cobo CLI, run the following command in your terminal:

```bash
cobo [OPTIONS] COMMAND [ARGS]...
```

Check full documentation [here](https://www.cobo.com/developers/v2/developer-tools/cobo-cli/introduction).

### Global Options

- `-e, --env [dev|prod]`: Override the environment for this command.
- `-a, --auth [apikey|user|org]`: Override the authentication method for this command.
- `--enable-debug`: Enable debug mode for verbose logging.
- `--config-file FILEPATH`: Specify the path to the config file.
- `--spec PATH`: Path to a custom OpenAPI specification file.
- `--help`: Show help message and exit.

## Commands

### Application Management

- **app**: Manage Cobo applications.
  - `init`: Create a new Cobo application project.
  - `run`: Run a Cobo application.
  - `upload`: Upload a Cobo application.
  - `update`: Update an existing Cobo application.
  - `status`: Check the status of a Cobo application.

### Authentication

- **auth**: Set or view the default authentication method.

### Configuration

- **config**: Manage CLI configuration settings.
  - `set`: Set a configuration value.
  - `get`: Get a configuration value.
  - `list`: List all configuration values.
  - `delete`: Delete a configuration value.
  - `show-path`: Show the configuration file path.
  - `env`: Print env vars for SDK samples. Use `--format shell` (default) / `powershell` / `cmd` for your platform; then `eval $(cobo config env)` or the doc-recommended command.

### Login and Logout

- **login**: Perform user or organization login operations.
  - `status`: Show the current login status.
  - `switch-org`: Switch between logged-in organizations.
- **logout**: Perform user or organization logout operations.

### API Requests

- **get**: Make a GET request to a Cobo API endpoint.
- **post**: Make a POST request to a Cobo API endpoint.
- **put**: Make a PUT request to a Cobo API endpoint.
- **delete**: Make a DELETE request to a Cobo API endpoint.
- **graphql**: Execute a GraphQL query against the Cobo API.

### Documentation

- **doc**: Open Cobo documentation or display API operation information.

### Environment

- **env**: Set or view the current environment.

### Logs

- **logs**: Commands related to log operations.
  - `tail`: Tail the request logs from Cobo.

### Webhook

- **webhook**: Commands related to webhook operations.
  - `events`: List all available webhook event types.
  - `listen`: Listen for webhook events using WebSocket.
  - `trigger`: Manually trigger a webhook event.

### AI Coding Agent Integration

- **skill**: Install and manage AI coding agent skills.
  - `install`: Install cobo-waas skill for an AI coding agent (claude, cursor, or all).
  - `list`: List available skills.
  - `remove`: Remove installed skill from an AI coding agent.
  - `status`: Show skill installation status.

### Other Commands

- **open**: Open a specific Cobo portal page in the default web browser.
- **keys**: Generate and manage API/APP keys.
  - `generate`: Generate a new API/APP key pair.
- **version**: Display the current version of the Cobo CLI tool.

## AI Coding Agent Setup

After installing cobo-cli, you can install the WaaS skill for your AI coding assistant:

```bash
# Install globally for Claude Code
cobo skill install claude

# Install in current project only
cobo skill install claude --scope local

# Install for all supported agents
cobo skill install all

# Check installation status
cobo skill status

# Remove skill
cobo skill remove claude
```

The skill enables AI agents (Claude Code, Cursor) to:
- Set up Cobo API authentication
- Create and manage wallets (Custodial, MPC)
- Execute transfers and monitor transactions
- Generate SDK code in Python, JavaScript, Go, Java

## Development

You can build your custom Cobo CLI based on the [Cobo CLI](https://github.com/CoboGlobal/cobo-cli) project.
You need to install [Poetry](https://python-poetry.org/docs/#installation) first.

To set up the development environment, install the development dependencies:

```bash
poetry install
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
