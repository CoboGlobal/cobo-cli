# State Inspection and Diagnostics

This guide helps agents verify current Cobo CLI setup state and diagnose issues.

## Quick Diagnostics Checklist

Run these commands in order to assess the current state:

```bash
# 1. CLI Installation
cobo version
# Expected: cobo-cli, version X.Y.Z

# 2. Configuration State
cobo config list
# Expected: Shows env, auth_method, api_key, api_secret

# 3. API Connectivity
cobo get /wallets --limit 1
# Expected: JSON response (may be empty array)

# 4. Auth Validation
cobo get /wallets/{any_valid_wallet_id}
# Expected: Wallet details or 404 (not 401/403)
```

## Diagnostic Commands

### Check CLI Installation

```bash
cobo version
```

| Output | State | Action |
|--------|-------|--------|
| `cobo-cli, version X.Y.Z` | Installed | Continue |
| `command not found` | Not installed | `pip install cobo-cli` |
| `ModuleNotFoundError` | Broken install | `pip uninstall cobo-cli && pip install cobo-cli` |

### Check Configuration

```bash
cobo config list
```

| Output | State | Action |
|--------|-------|--------|
| Shows env, auth_method, keys | Configured | Continue |
| Empty or minimal | Not configured | Run setup |
| Missing api_key/api_secret | Keys not generated | `cobo keys generate --key-type API` |
| Missing auth_method | Auth not set | `cobo auth apikey` |

### Check Environment

```bash
cobo config list | grep "^environment:"
```

| Output                 | Environment | API Host |
|------------------------|-------------|----------|
| `environment: sandbox` | Sandbox | api.sandbox.cobo.com |
| `environment: dev`     | Development | api.dev.cobo.com |
| `environment: prod`    | Production | api.cobo.com |
| No output              | Not set | `cobo env dev` |

### Check Auth Method

```bash
cobo config list | grep "^auth_method:"
```

| Output                | Method | Use Case |
|-----------------------|--------|----------|
| `auth_method: apikey` | API key | Automation |
| `auth_method: user`   | User token | Portal access |
| `auth_method: org`    | Org token | Portal apps |
| `auth_method: none`   | No auth | Public endpoints |
| No output             | Not set | `cobo auth apikey` |

### Check API Keys

```bash
# Check if keys exist (without exposing values)
cobo config list | grep -E "^api_(key|secret):" | cut -d= -f1
```

| Output | State | Action |
|--------|-------|--------|
| Both `api_key` and `api_secret` | Keys present | Verify registration |
| Only `api_key` | Secret missing | Regenerate keys |
| Neither | Keys not generated | `cobo keys generate --key-type API` |

## API Connectivity Tests

### Basic Connectivity

```bash
cobo get /wallets --limit 1
```

| Result | Diagnosis | Action |
|--------|-----------|--------|
| JSON response | API working | Continue |
| Connection error | Network issue | Check VPN, proxy, firewall |
| Timeout | Slow network or API | Retry, check status page |

### Auth Validation

```bash
cobo get /wallets --limit 1
```

| HTTP Status | Diagnosis | Action |
|-------------|-----------|--------|
| 200 | Auth working | Setup complete |
| 401 | Auth failed | Check keys, register in Portal |
| 403 | Permissions | Update key permissions in Portal |
| 404 | Endpoint issue | Check API version |

### Environment Validation

```bash
# Verify environment by checking accessible resources
cobo get /wallets --limit 1
```

If you get unexpected results:
- Wallets missing that should exist → Wrong environment
- 401 error → Key not registered in current environment

## Full Diagnostic Script

```bash
#!/bin/bash
echo "=== Cobo CLI Diagnostics ==="

echo -e "\n1. Version:"
cobo version 2>&1

echo -e "\n2. Environment:"
cobo config list | grep "^environment:" || echo "NOT SET"

echo -e "\n3. Auth Method:"
cobo config list | grep "^auth_method:" || echo "NOT SET"

echo -e "\n4. API Keys:"
cobo config list | grep -E "^api_(key|secret):" | cut -d= -f1 | sort

echo -e "\n5. Connectivity Test:"
cobo get /wallets --limit 1 2>&1 | head -5

echo -e "\n=== End Diagnostics ==="
```

## State Matrix

| Env Set | Auth Set | Keys Present | Keys Registered | State |
|---------|----------|--------------|-----------------|-------|
| No | No | No | - | Fresh install |
| Yes | No | No | - | Partial setup |
| Yes | Yes | No | - | Missing keys |
| Yes | Yes | Yes | No | Keys not registered |
| Yes | Yes | Yes | Yes | Ready |

## Common Diagnostic Scenarios

### Scenario 1: Fresh Install

**Symptoms**: `cobo config list` shows empty or minimal output

**Diagnosis**:
```bash
cobo config list
# Output: (empty or only default values)
```

**Resolution**:
```bash
cobo env dev
cobo keys generate --key-type API
cobo open developer  # Register key
cobo auth apikey
```

### Scenario 2: Keys Not Registered

**Symptoms**: 401 errors, but keys exist in config

**Diagnosis**:
```bash
# Keys exist
cobo config list | grep api_key
# Output: api_key=abc123...

# But auth fails
cobo get /wallets --limit 1
# Output: 401 Unauthorized
```

**Resolution**:
```bash
cobo open developer
# Register the public key shown in config
```

### Scenario 3: Wrong Environment

**Symptoms**: Resources not found that should exist

**Diagnosis**:
```bash
# Check environment
cobo config list | grep env
# Output: env=dev

# But resources are in prod
# Switch environment or verify where resources exist
```

**Resolution**:
```bash
cobo env prod  # If resources are in prod
# Or verify resources in dev
cobo get /wallets --limit 50
```

### Scenario 4: Permissions Issue

**Symptoms**: 403 Forbidden on specific operations

**Diagnosis**:
```bash
# List works
cobo get /wallets --limit 1
# Output: 200 OK

# But create fails
cobo post /wallets --name "Test" --wallet_type Custodial --wallet_subtype Asset
# Output: 403 Forbidden
```

**Resolution**:
```bash
cobo open developer
# Edit API key permissions to include required scopes
```

## Environment-Specific Checks

### Development Environment

```bash
cobo env dev
cobo config list | grep env
# Expected: env=dev

cobo get /wallets --limit 1
# Should work with dev-registered key
```

### Production Environment

```bash
cobo env prod
cobo config list | grep env
# Expected: env=prod

# CAUTION: Production affects real assets
cobo get /wallets --limit 1
# Should work with prod-registered key
```

## Diagnostic Output Format

When reporting diagnostic results, use this format:

```json
{
  "diagnostics": {
    "cli_installed": true,
    "cli_version": "1.2.3",
    "env": "dev",
    "auth_method": "apikey",
    "keys_present": true,
    "keys_registered": true,
    "api_connectivity": "ok",
    "issues": []
  },
  "next_steps": []
}
```

Example with issues:

```json
{
  "diagnostics": {
    "cli_installed": true,
    "cli_version": "1.2.3",
    "env": "dev",
    "auth_method": "apikey",
    "keys_present": true,
    "keys_registered": false,
    "api_connectivity": "401",
    "issues": ["API key not registered in Portal"]
  },
  "next_steps": [
    "Run: cobo open developer",
    "Add the public key as an API key",
    "Verify with: cobo get /wallets --limit 1"
  ]
}
```
