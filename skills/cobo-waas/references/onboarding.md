# First-Time Setup Guide

This guide helps agents onboard new users to Cobo CLI with a decision-tree approach.

## Quick State Detection

Run these commands to determine current setup state:

```bash
# 1. Is CLI installed?
cobo version
# Expected: cobo-cli, version X.Y.Z
# If fails: pip install cobo-cli

# 2. Is it configured?
cobo config list
# Expected: Shows env, auth_method, api_key/api_secret
# If empty: Needs configuration

# 3. Does auth work?
cobo get /wallets --limit 1
# Expected: JSON response with wallets array
# If 401/403: Auth not configured or key not registered
```

## Decision Tree

```
Is CLI installed? (cobo version)
├── No → pip install cobo-cli → Continue
└── Yes
    ↓
Is environment set? (cobo config list → check 'env')
├── No → Choose environment (see below) → Continue
└── Yes
    ↓
Is auth method set? (cobo config list → check 'auth_method')
├── No → Choose auth method (see below) → Continue
└── Yes
    ↓
Does auth work? (cobo get /wallets --limit 1)
├── 401/403 → Key not registered in Portal → Register key
├── Connection error → Check network/VPN
└── Success → Ready to use!
```

## Environment Selection

| Environment | Host | Use Case |
|-------------|------|----------|
| `sandbox` | api.sandbox.cobo.com | Isolated testing, no real assets |
| `dev` | api.dev.cobo.com | Development with test assets |
| `prod` | api.cobo.com | Production with real assets |

**Recommendation**: Start with `dev` for most development work.

```bash
# Set environment
cobo env dev

# Verify
cobo config list
```

## Auth Method Selection

| Method | Use Case | Requires |
|--------|----------|----------|
| `apikey` | Automation, scripts, CI/CD | API keypair registered in Portal |
| `user` | Interactive Portal access | Browser login |
| `org` | Portal apps (Cobo Apps) | App context + org login |
| `none` | Public endpoints only | Nothing |

**Recommendation**: Use `apikey` for automation workflows.

## API Key Setup (Recommended for Agents)

### Step 1: Generate Keypair

```bash
cobo keys generate --key-type API
```

Output:
```
API Key (Public Key): <64-char hex>
API Secret (Private Key): <64-char hex>
```

**IMPORTANT**: The secret is only shown once. Store it securely.

### Step 2: Register Public Key

**Option A: CLI (dev/sandbox environments, recommended)**

```bash
# Login first (if not already logged in)
cobo login --user

# Register the key directly from CLI
cobo keys register
# Or specify a pubkey: cobo keys register --pubkey <hex>
```

**Option B: Portal (all environments)**

```bash
# Open Developer Console
cobo open developer
```

In the Portal:
1. Go to Developer Console → API Keys
2. Click "Add API Key"
3. Paste the **public key** (NOT the secret)
4. Select permissions (e.g., "All" for development)
5. Save

### Step 3: Configure CLI Auth

```bash
# Set auth method
cobo auth apikey

# Verify config shows api_key and api_secret
cobo config list
```

### Step 4: Verify Setup

```bash
# Test API call
cobo get /wallets --limit 1
```

Expected: JSON response (may be empty array if no wallets exist)

## Verification Checklist

Run all checks to confirm setup:

```bash
# Check 1: CLI version
cobo version

# Check 2: Environment
cobo config list | grep env

# Check 3: Auth method
cobo config list | grep auth_method

# Check 4: API connectivity
cobo get /wallets --limit 1

# Check 5: Can create resources (optional)
cobo post /wallets --describe  # Should show required params
```

## Common First-Time Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `command not found: cobo` | CLI not installed | `pip install cobo-cli` |
| `No api_key in config` | Keys not generated | `cobo keys generate --key-type API` |
| `401 Unauthorized` | Key not registered in Portal | Register public key in Developer Console |
| `403 Forbidden` | Key lacks permissions | Update key permissions in Portal |
| Empty config output | Fresh install | Run environment and auth setup |

## Quick Start Commands

For a brand new setup, run these in order:

```bash
# 1. Install
pip install cobo-cli

# 2. Set environment
cobo env dev

# 3. Generate keys
cobo keys generate --key-type API
# Save the output securely!

# 4. Register key (dev/sandbox: CLI; prod: Portal)
cobo login --user && cobo keys register
# Or for prod: cobo open developer → Add the PUBLIC key as an API key

# 5. Set auth method
cobo auth apikey

# 6. Verify
cobo get /wallets --limit 1
```

## Next Steps

After successful setup:
- Create your first wallet: See `recipes.md`
- Explore API endpoints: `cobo get --list`
- Set up webhooks: `cobo webhook events`
