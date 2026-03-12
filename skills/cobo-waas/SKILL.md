---
name: cobo-waas
description: Use when interacting with Cobo WaaS 2.0 or Cobo Portal via cobo-cli. Optimized for agentic coding tools (Claude Code, Codex, Cursor, Gemini CLI) with CLI-first workflows for config, keys, wallets, transfers, logs, and GraphQL.
---

# Cobo WaaS Skill

This skill uses `cobo-cli` to perform WaaS 2.0 and Portal tasks (wallets, transfers, logs). It is self-contained for agentic coding tools (Claude Code, Codex, Cursor, Gemini CLI).

## Quick Start

Fastest path to your first API call:

```bash
# 1. Verify installation
cobo version                           # If fails: pip install cobo-cli

# 2. Set environment
cobo env dev                           # Use dev for testing

# 3. Generate API keys
cobo keys generate --key-type API      # Save the output!

# 4. Register key in Portal
cobo open developer                    # Add the PUBLIC key as API key

# 5. Set auth method
cobo auth apikey

# 6. Test it works
cobo get /wallets --limit 1            # Should return JSON
```

**Run SDK samples (Python/Node/Go/Java):** load env from config once, then run your script in the same shell:

- **macOS / Linux (bash, zsh):** `eval $(cobo config env)`
- **Windows PowerShell:** `cobo config env --format powershell | Invoke-Expression`
- **Windows CMD:** `cobo config env --format cmd > env.bat && env.bat`

Then e.g. `python your_script.py` or `node app.js`.

## When to Use

- The user wants to interact with Cobo WaaS 2.0 or Portal using the CLI
- The task needs a CLI-only path instead of MCP
- The task includes configuring env/auth, generating keys, wallet operations, transfers, logs, or GraphQL queries
- The user wants to generate SDK code for Python, Node.js, Go, or Java

## State Detection

Before starting, determine the current setup state:

```bash
# Is CLI installed?
cobo version

# Is it configured?
cobo config list

# Does auth work?
cobo get /wallets --limit 1
```

| Result | State | Next Step |
|--------|-------|-----------|
| `command not found` | CLI not installed | `pip install cobo-cli` |
| Config empty | Not configured | Run Quick Start |
| 401 error | Keys not registered | `cobo keys register` (dev/sandbox) or register in Portal |
| error_code 2024 | Unauthorized | Perform authorization operations |
| JSON response | Ready | Proceed with task |

For detailed diagnostics, see `references/diagnostics.md`.

## Before Generating API Requests (reduce errors)

**Always look up the endpoint’s parameters before generating CLI or SDK code.**

1. **Identify the API path** from the user’s intent (e.g. “list wallets” → `GET /wallets`, “create wallet” → `POST /wallets`).
2. **Look up parameters:** run `cobo doc <path>` (e.g. `cobo doc /wallets`) and read the printed operation description (parameters, types, required/optional).
3. **Then generate** the exact `cobo get/post ...` or SDK call using those parameter names and types.

Example: before writing `cobo get /wallets ...` or SDK code for listing wallets, run `cobo doc /wallets` and use the output to build the correct query (e.g. `limit`, `cursor`). This reduces wrong parameter names, wrong types, and missing required fields.

## Reference Navigation

Choose the right reference for your task:

| Task | Reference File |
|------|---------------|
| First-time setup | `references/onboarding.md` |
| Check current state | `references/diagnostics.md` |
| Handle credentials safely | `references/security.md` |
| Common API endpoints | `references/api-quickref.md` |
| Understand terminology | `references/concepts.md` |
| End-to-end workflows | `references/recipes.md` |
| Fix errors | `references/errors.md`, `references/troubleshooting.md` |
| CLI command syntax | `references/cli.md` |
| Auth setup details | `references/auth.md` |
| GraphQL queries | `references/graphql.md` |
| Generate SDK code | `references/sdk-patterns.md`, `references/samples/*` |

## SDK / generated code rules (avoid over-engineering)

Applies to **all languages** (Python, Node.js, Go, Java). When generating SDK or script code, **follow the template for that language exactly**; do not add extra structure the user did not ask for.

1. **Use the template as the single source of style.** For each language the canonical style is in `assets/templates/` (`python.md`, `ts-node.md`, `go.md`, `java.md`). Copy the **minimal** setup and one short block per operation (e.g. list wallets = a few lines: call the API, then a short loop or print). Same requirement for Python, Node/TS, Go, and Java.
2. **Do not add** unless the user explicitly asks (in any language):
   - Wrapper/helper functions that hide the API (e.g. `getClient()`, `listWallets(api, ...)`)
   - Every optional parameter in signatures — only pass what the task needs (e.g. `limit=10`)
   - Converting responses to custom shapes (e.g. plain dict/JSON, custom DTOs)
   - Long module/function docstrings, usage instructions in comments, or heavy error handling
3. **Match the template snippet length.** In every language, template examples are a few lines per operation. Generated code should be the same size unless the user asks for more.
4. **When in doubt, generate less.** Prefer the minimal version from the template for that language; the user can ask for more structure or error handling if needed.

## Use-case Oriented Workflow

Pick the smallest slice that solves the task:

1. **Configure environment and auth** - `references/onboarding.md`
2. **Generate and validate keypair** - `references/auth.md`
3. **Discover and describe API endpoints** - Run `cobo doc <path>` (e.g. `cobo doc /wallets`) for parameter details, then `references/cli.md`
4. **Create wallets and addresses** - `references/recipes.md` Recipe 2-3
5. **Create transfers and check status** - `references/recipes.md` Recipe 4-5
6. **Debug failures** - `references/errors.md`, `references/troubleshooting.md`
7. **Set up webhooks** - `references/recipes.md` Recipe 7
8. **Run GraphQL queries** - `references/graphql.md`
9. **Generate SDK code** - `references/sdk-patterns.md`, `references/samples/*`

## Output Format for Agents

After each action, return a short JSON object:

### Success Response

```json
{
  "action": "create_wallet",
  "status": "ok",
  "ids": {
    "wallet_id": "f47ac10b-58cc-..."
  },
  "links": {
    "portal_wallet_url": "https://portal.cobo.com/wallets/f47ac10b-..."
  },
  "next_step": "Create address with: cobo post /wallets/{wallet_id}/addresses --chain_id ETH",
  "notes": "Custodial Asset wallet created successfully"
}
```

### Error Response

```json
{
  "action": "create_wallet",
  "status": "error",
  "error": {
    "code": 401,
    "message": "Unauthorized"
  },
  "diagnosis": "API key not registered in Portal",
  "recovery": "Register public key: cobo keys register (dev/sandbox) or cobo open developer (prod)",
  "reference": "references/errors.md#401-unauthorized"
}
```

### Error Code Response Format

API responses may include both HTTP status codes and business error codes (`error_code`). They serve different purposes:

- **HTTP Status Code**: Indicates the HTTP-level result (200=success, 4xx=client error, 5xx=server error)
- **Business Error Code (`error_code`)**: Provides specific business logic error details in the response body

Example error response with both:
```json
{
  "error_code": 2024,
  "error_message": "Unauthorized",
  "error_id": "48d1f0c3382f4c50a11ff529a2c3a65a"
}
```
HTTP status: 401 Unauthorized

## Recovery Patterns

When operations fail, follow this pattern:

1. **Identify the error** - Check HTTP status code, `error_code` in response body, and message
2. **Diagnose** - Run relevant diagnostic commands
3. **Consult reference** - Check `references/errors.md` or `references/troubleshooting.md`
4. **Apply fix** - Follow the recovery steps based on error type
5. **Verify** - Re-run the original operation

### HTTP Status Code Recovery

| HTTP Status | Description | Quick Fix |
|-------------|-------------|-----------|
| 200 | Success | No action needed |
| 400 | Bad Request | Check request parameters: `cobo post /path --describe` |
| 401 | Unauthorized | Check API Key, API signature, or timestamp. Generate keys: `cobo keys generate --key-type API` + register: `cobo keys register` (dev/sandbox) or Portal |
| 403 | Forbidden | Check key permissions in Portal: `cobo open developer` |
| 404 | Not Found | Verify endpoint: `cobo get --list` |
| 405 | Method Not Allowed | Use supported HTTP method (GET, POST, etc.) |
| 406 | Not Acceptable | Ensure request content format is JSON |
| 429 | Too Many Requests | Reduce request frequency and retry later |
| 500 | Internal Server Error | Check server configuration, including Org Access Tokens expiration, then retry |
| 502 | Bad Gateway | Check connection and retry later |
| 503 | Service Unavailable | Retry later |

### Business Error Code Recovery

When response includes `error_code` field, use specific recovery steps:

| Error Code | Description | Solution |
|------------|-------------|----------|
| 1000 | Internal server error (may include Org Access Tokens expired) | Check server configuration, verify Org Access Tokens, retry later |
| 1003, 2003 | Missing required parameters | Provide all required parameters |
| 1006, 2006 | Invalid parameter format or unsupported values | Provide valid parameters in expected format |
| 2000 | Internal error during processing | Retry later |
| 2002 | Unsupported HTTP method | Use supported HTTP method |
| 2010 | Rate limit exceeded | Retry later |
| 2021 | Request handler missing or not implemented | Provide valid handler for request |
| 2022 | Missing required request headers | Include all required request headers |
| 2023 | API signature missing or invalid | Verify API signature is correct. Reference signature calculation guide |
| 2024 | API Key authentication failed | 1. Use API Key matching current environment (dev/prod)<br>2. Ensure API Key is registered and active<br>3. If permanent API Key, ensure request from whitelisted IP<br>Register: `cobo keys register` (dev/sandbox) or `cobo open developer` (prod) |
| 2025, 4001 | Forbidden access to requested resource | Check permissions associated with API Key. Reference permissions guide |
| 2026 | Too many requests | Retry later |
| 2028 | Requested resource not found | Check request URL |
| 2029 | Invalid status attribute provided | Provide valid value for status attribute |
| 2040 | Resource with same key already exists | Use unique key |
| 2050, 2052 | No available plan or usage limit exceeded | Purchase plan or upgrade existing plan |
| 2051 | Current plan expired | Renew plan to continue service |
| 30001, 12009 | Duplicate request ID | Use unique request ID: `tx-$(date +%s)-$(openssl rand -hex 4)` |
| 30007 | Invalid amount (not valid number or wrong format/range) | Provide valid amount in expected format and range |
| 30008 | Invalid absolute amount (too small/large or zero when non-zero required) | Ensure absolute amount meets required conditions |
| 30010 | Amount below dust threshold | Increase amount to exceed dust threshold |
| 30011 | Amount below minimum deposit threshold | Increase deposit amount to meet minimum threshold |
| 30012, 12007 | Insufficient balance for requested operation | Ensure source address has sufficient balance for transfer amount |
| 30013 | Insufficient balance to pay transaction fees | Ensure source address has sufficient balance for transaction fees |
| 30014 | Invalid destination address | Provide valid destination address |
| 30023 | Invalid trading account type (Exchange wallets only) | Provide valid trading account type |
| 30032 | Invalid private key share holder group (MPC wallets only) | Check if valid master or signing group is configured |
| 4001 | Forbidden access to requested resource | Check permissions associated with API Key |
| 60010 | Specified token not enabled for this team | Enable token for your team |
| 12002 | Cobo does not support specified token | Select supported token. Call List supported tokens endpoint |
| 12025 | Invalid UTXO specified in included_utxos or excluded_utxos | Verify UTXOs specified in included_utxos or excluded_utxos |

### Common Error Code Combinations

Some errors may return multiple error codes indicating the same issue:
- **1003, 2003**: Missing required parameters
- **1006, 2006**: Invalid parameter format
- **12007, 30012**: Insufficient balance
- **12009, 30001**: Duplicate request ID
- **2025, 4001**: Forbidden access
- **2050, 2052**: Plan limit issues

## SDK Bridge

When to transition from CLI to SDK:

| Scenario | Recommendation |
|----------|----------------|
| One-off operations | CLI |
| Quick exploration | CLI |
| Production automation | SDK |
| Complex workflows | SDK |
| Error handling needed | SDK |

To generate SDK code:
1. Consult `references/sdk-patterns.md` for patterns
2. Use `references/samples/{python,ts-node,go,java}.md` for complete examples

## Guardrails

**Security:**
- Never echo secrets or private keys in output
- Redact `api_secret` values: show as `[REDACTED]`
- Check `references/security.md` for credential handling rules

**Environment:**
- Always confirm the target environment (sandbox, dev, prod)
- Production affects real assets - verify before operations
- Prefer dev/sandbox for testing

**Idempotency:**
- Use unique `request_id` for transactions: `tx-$(date +%s)-$(openssl rand -hex 4)`
- Never reuse request_ids to avoid duplicate transactions

**Error Handling:**
- Always check both HTTP status code and `error_code` in response body
- When encountering `error_code: 2024` or HTTP 401, perform authorization operations
- Provide specific recovery steps based on error code (see Recovery Patterns section)
- For rate limiting (429, 2010, 2026), implement exponential backoff retry logic
- For duplicate request ID errors (30001, 12009), generate new unique request_id and retry

## References

| Reference | Description |
|-----------|-------------|
| `references/onboarding.md` | First-time setup guide with decision tree |
| `references/diagnostics.md` | State inspection and quick checks |
| `references/security.md` | Credential handling guardrails |
| `references/api-quickref.md` | Common endpoint quick reference |
| `references/concepts.md` | Glossary and terminology |
| `references/recipes.md` | End-to-end workflow recipes |
| `references/troubleshooting.md` | Decision tree diagnostics |
| `references/errors.md` | Comprehensive error catalog |
| `references/cli.md` | CLI command patterns |
| `references/auth.md` | Auth and key setup |
| `references/graphql.md` | GraphQL usage |
| `references/sdk-patterns.md` | SDK vibe coding guide |
| `references/samples/python.md` | Python SDK examples |
| `references/samples/ts-node.md` | Node.js/TypeScript SDK examples |
| `references/samples/go.md` | Go SDK examples |
| `references/samples/java.md` | Java SDK examples |
