# Credential Handling and Security

This document provides security guardrails for AI agents working with Cobo CLI and WaaS APIs.

## Never-Do List

**NEVER do any of the following:**

1. **Echo secrets to console or logs**
   ```bash
   # WRONG - exposes secret
   echo $COBO_API_SECRET
   cat ~/.cobo/config.toml | grep api_secret

   # RIGHT - only reference existence
   cobo config list | grep -q api_secret && echo "Secret is set"
   ```

2. **Store secrets in git**
   ```bash
   # WRONG - secrets in repo
   git add .cobo/config.toml
   git add .env

   # RIGHT - use .gitignore
   echo ".cobo/" >> .gitignore
   echo ".env" >> .gitignore
   ```

3. **Include secrets in agent output**
   ```json
   // WRONG
   {"api_secret": "abc123..."}

   // RIGHT
   {"api_secret": "[REDACTED]"}
   ```

4. **Pass secrets as command-line arguments**
   ```bash
   # WRONG - visible in process list
   cobo --api-secret abc123 get /wallets

   # RIGHT - use config file or env vars
   export COBO_API_SECRET=abc123
   cobo get /wallets
   ```

5. **Log full config contents**
   ```bash
   # WRONG
   cobo --enable-debug get /wallets 2>&1 | tee debug.log

   # RIGHT - review debug output before sharing
   cobo --enable-debug get /wallets
   ```

## Config File Locations

| File | Location | Contains |
|------|----------|----------|
| Main config | `~/.cobo/config.toml` | environment, auth_method, api_key, api_secret |
| SDK config | Various | Depends on SDK |

### Config File Permissions

```bash
# Ensure config is readable only by owner
chmod 600 ~/.cobo/config.toml
chmod 600 .env

# Verify permissions
ls -la ~/.cobo/config.toml
# Expected: -rw------- (600)
```

## Secure Key Generation

### Using CLI (Recommended)

```bash
# Generate and store automatically
cobo keys generate --key-type API
```

The CLI:
- Generates a cryptographically secure Ed25519 keypair
- Stores keys in `~/.cobo/config.toml`
- Displays keys only once during generation

### Manual Generation

```bash
# If you need to generate keys manually
openssl genpkey -algorithm ed25519 -outform DER | xxd -p -c 64
```

## Environment Variables

### Supported Variables (CLI)

| Variable | Purpose | Example |
|----------|---------|---------|
| `COBO_API_SECRET` | API private key (hex) | `abc123...` (64 chars) |
| `COBO_API_KEY` | API public key (hex) | `def456...` (64 chars) |
| `COBO_ENVIRONMENT` | Environment | `dev`, `prod`, `sandbox` |
| `COBO_AUTH_METHOD` | Auth method | `apikey`, `user`, `org`, `none` |
| `COBO_API_HOST` | Custom API host | `https://api.dev.cobo.com` |

### Setting Environment Variables

```bash
# For current session
export COBO_API_SECRET="<your-secret-hex>"
export COBO_ENVIRONMENT="dev"

# For persistent use (add to shell profile)
echo 'export COBO_API_SECRET="<your-secret-hex>"' >> ~/.bashrc

# Note: cobo-cli does not auto-load `.env` for CLI config.
# Use environment variables or `cobo config set` instead.
```

### Precedence Order

1. Environment variables (highest)
2. `~/.cobo/config.toml` (lowest)

## Output Redaction Rules

When generating output for users, agents MUST redact:

| Field | Action | Example |
|-------|--------|---------|
| `api_secret` | Full redact | `[REDACTED]` |
| `api_key` | Partial show | `abc1...xyz9` |
| `private_key` | Full redact | `[REDACTED]` |
| `mnemonic` | Full redact | `[REDACTED]` |
| `password` | Full redact | `[REDACTED]` |

### Redaction Example

```json
// Input (from cobo config list)
{
  "env": "dev",
  "api_key": "abc123def456...",
  "api_secret": "secret789xyz..."
}

// Output (agent response)
{
  "env": "dev",
  "api_key": "abc1...6789",
  "api_secret": "[REDACTED]"
}
```

## Secure Workflow Patterns

### Pattern 1: Fresh Setup

```bash
# 1. Generate keys (only time secret is shown)
cobo keys generate --key-type API
# Copy and securely store the secret!

# 2. Set auth
cobo auth apikey

# 3. Verify without exposing
cobo config list | grep -E "^(env|auth_method)="
```

### Pattern 2: Script Configuration

```bash
#!/bin/bash
# Load from environment, never hardcode
if [ -z "$COBO_API_SECRET" ]; then
    echo "Error: COBO_API_SECRET not set"
    exit 1
fi

cobo get /wallets --limit 10
```

### Pattern 3: CI/CD

```yaml
# GitHub Actions example
env:
  COBO_API_SECRET: ${{ secrets.COBO_API_SECRET }}
  COBO_ENV: dev

steps:
  - run: cobo get /wallets --limit 1
```

## Security Checklist

Before any operation:

- [ ] Secrets are not in command-line arguments
- [ ] Config file permissions are restricted (600)
- [ ] `.gitignore` includes `.cobo/` and `.env`
- [ ] Agent outputs redact sensitive fields
- [ ] Environment is confirmed (dev vs prod)
- [ ] Debug logs are not shared without review

## Incident Response

If a secret is exposed:

1. **Immediately revoke the key**
   ```bash
   cobo open developer
   # Delete the compromised API key in Portal
   ```

2. **Generate new keys**
   ```bash
   cobo keys generate --key-type API
   # Register new public key in Portal
   ```

3. **Audit recent activity**
   ```bash
   cobo logs tail
   # Review for unauthorized operations
   ```

4. **Update all references**
   - Update CI/CD secrets
   - Update environment variables
   - Update any scripts using the old key
