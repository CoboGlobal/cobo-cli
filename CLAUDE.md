# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cobo CLI is a command-line interface for managing Cobo Wallet-as-a-Service (WaaS) 2.0. It's built with Python using Click for the CLI framework and Poetry for dependency management.

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Testing
```bash
# Run all tests
poetry run pytest cobo_cli/tests

# Run tests with coverage
poetry run pytest --cov=cobo_cli cobo_cli/tests

# Run specific test file
poetry run pytest cobo_cli/tests/test_cli_integration.py

# Run tox for multiple Python versions
tox
```

### Code Quality
```bash
# Format code with black
poetry run black cobo_cli

# Sort imports
poetry run isort cobo_cli

# Lint with flake8
poetry run flake8 cobo_cli

# Security scan with bandit
poetry run bandit -r cobo_cli -c .bandit_scan.cfg

# Run pre-commit hooks manually
poetry run pre-commit run --all-files
```

### Running the CLI Locally
```bash
# Install in development mode
poetry install

# Run CLI
poetry run cobo --help

# Or after activating shell
cobo --help
```

## Architecture

### Core Components

**CLI Entry Point (`cli.py`)**
- Main Click group that orchestrates all commands
- Sets up `CommandContext` which flows through all commands via Click's context object
- Handles global options: `--env`, `--auth`, `--enable-debug`, `--config-file`, `--spec`
- Loads configuration and API spec before command execution

**CommandContext (`data/context.py`)**
- Dataclass that carries runtime state between commands
- Contains: `env` (EnvironmentType), `auth_method` (AuthMethodType), `config_manager` (ConfigManager), `api_spec` (optional dict)
- Accessed in commands via `ctx.obj`

**Configuration System (`utils/config.py`)**
- `ConfigManager` handles TOML config file at `~/.cobo/config.toml`
- `CoboSettings` uses Pydantic for validation and environment variable support
- Configuration is environment-aware (sandbox/dev/prod)

**Authentication Flow (`utils/authorization.py`)**
- Three auth methods: `apikey`, `user`, `org`
- OAuth flow for user/org authentication with browser-based authorization
- `initiate_auth()` → `poll_for_token()` pattern for async token retrieval

**API Request Layer (`utils/api.py`)**
- `make_request()` is the central function for all API calls
- Handles three authentication methods differently:
  - `apikey`: Uses API key/secret from config with custom signature headers (Biz-Api-*)
  - `org`: Requires app directory with manifest.json + .env file, uses app credentials + org token
  - `user`: Uses bearer token from user login
- Path parameter substitution and signature generation using `Signer`

**Manifest System (`data/manifest.py`)**
- Pydantic model for Cobo app manifests (manifest.json)
- Validates app metadata: name, descriptions, URLs, permissions, wallet types
- Supports different grant dimensions (org/user) and wallet types
- Used by app commands for creating, uploading, and managing apps

**OpenAPI Integration (`utils/openapi.py`)**
- Dynamically loads OpenAPI spec (bundled or custom via `--spec`)
- Used for API documentation and parameter validation
- Resolves JSON references in spec files

### Command Structure

Commands are organized in `commands/` directory:
- **App lifecycle**: `app.py` - init, run, upload, update, status
- **Authentication**: `auth.py`, `login.py`, `logout.py`
- **Configuration**: `config.py`, `env.py`
- **API operations**: `get.py`, `post.py`, `put.py`, `delete.py`, `graphql.py`
- **Keys**: `keys.py` - generate API/APP key pairs
- **Webhooks**: `webhook.py` - events, listen, trigger
- **Logs**: `logs.py` - tail request logs
- **Documentation**: `doc.py`, `open.py`

### Authentication Methods

The CLI supports three authentication methods (defined in `data/auth_methods.py`):

1. **apikey**: API key/secret pairs stored in config, suitable for server-to-server
2. **user**: User access tokens obtained via OAuth, for user-specific operations
3. **org**: Organization access tokens, requires app context (manifest.json + .env)

The auth method can be set globally in config or overridden per-command with `--auth`.

### Environment System

Three environments (defined in `data/environments.py`):
- `sandbox`: Testing environment with default app ID
- `dev`: Development environment with default app ID
- `prod`: Production environment (no default app ID)

Environment affects which API host is used and which credentials are loaded from config.

## Important Patterns

### Context Passing
All commands receive `CommandContext` via Click's context:
```python
@click.command()
@click.pass_context
def my_command(ctx):
    command_context: CommandContext = ctx.obj
    config_manager = command_context.config_manager
```

### Making API Requests
Use `make_request()` from `utils/api.py`:
```python
from cobo_cli.utils.api import make_request

response = make_request(ctx, "GET", "/path", params={...})
```

### App Directory Requirements
Commands using org auth require:
- `manifest.json` with app metadata
- `.env` file with APP_SECRET and org tokens
- Validated via `validate_manifest_and_get_app_id()` in `utils/app.py`

### Signature Generation
API requests are signed using Ed25519:
- Signature input: `{METHOD}|{PATH}|{NONCE}|{PARAMS}|{BODY}`
- Headers: `Biz-Api-Key`, `Biz-Api-Nonce`, `Biz-Api-Signature`
- Implemented in `utils/signer.py`

## Testing Notes

- Tests are in `cobo_cli/tests/`
- Use pytest fixtures from `conftest.py`
- Mock Click context and CommandContext for command testing
- Integration tests in `test_cli_integration.py`
- Use `pytest-mock` for mocking API calls and file operations

## Configuration File

The config file at `~/.cobo/config.toml` has this structure:
```toml
[common]
environment = "dev"
auth_method = "apikey"

[dev]
api_key = "..."
api_secret = "..."
api_host = "https://api.dev.cobo.com"

[prod]
api_key = "..."
api_secret = "..."
api_host = "https://api.cobo.com"
```

Environment-specific sections override common settings.
