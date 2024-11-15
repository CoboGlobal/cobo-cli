# Cobo CLI

Cobo CLI is a command-line interface for managing Cobo applications and configurations.

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

To use the Cobo CLI, run the following command in your terminal:

```bash
cobo [OPTIONS] COMMAND [ARGS]...
```

Check full doc [here](https://www.cobo.com/developers/v2/developer-tools/cobo-cli/introduction)

### Global Options

- `-e, --env [sandbox|dev|prod]`: Override the environment for this command.
- `-a, --auth [apikey|user|org]`: Override the authentication method for this command.
- `--enable-debug`: Enable debug mode for verbose logging.
- `--config-file FILEPATH`: Specify the path to the config file.
- `--spec PATH`: Path to a custom OpenAPI specification file.
- `--help`: Show help message and exit.

## Commands

### Application Management

- **app**: Manage Cobo applications.
  - `init`: Create a new Cobo application project.
  - `run`: Run a Cobo application(not supported yet.).
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

### Other Commands

- **open**: Open a specific Cobo portal page in the default web browser.
- **keys**: Generate and manage API/APP keys.
  - `generate`: Generate a new API/APP key pair.
- **version**: Display the current version of the Cobo CLI tool.

## Development
[Install poetry first](https://python-poetry.org/docs/#installation)

To set up the development environment, install the development dependencies:

```bash
poetry install
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
