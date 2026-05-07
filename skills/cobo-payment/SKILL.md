---
name: cobo-payment
description: >
  Use when the user mentions pay-in orders, refunds, payouts, merchants,
  PSP balances, counterparties, destinations, allocations, settlement reports, payment links,
  or any /payments/* endpoint.
  Do NOT use for general wallet operations (list wallets, create addresses,
  transfers, staking, MPC vaults) — those belong to cobo-waas.
---
# Cobo Payment Skill

This skill uses `cobo-cli` to interact with Cobo Payment APIs (`/payments/*`). Auth and environment setup are shared with the cobo-waas skill.

## Quick Start

Auth and env setup is identical to cobo-waas:
```bash
cobo version                        # If fails: pip install cobo-cli
cobo env dev                        # Set environment
cobo login -u                       # OAuth login (opens browser)
cobo keys generate --key-type API   # Generate API key
cobo keys register                  # dev/sandbox only
cobo auth apikey                    # Set auth method
cobo get /payments/orders --limit 1 # Verify payment access
```

For production key registration: `cobo open developer` → add public key + grant Payment permissions.

## State Detection

**Run these checks first and fix issues automatically — do not ask the user to run them manually.**

```bash
cobo version
cobo config list
cobo get /payments/orders --limit 1
```

| Result | State | Auto-fix |
|--------|-------|----------|
| `command not found` | CLI not installed | `pip install cobo-cli` |
| Config empty | Not configured | Run Quick Start steps |
| `Key or secret not found` | Keys missing | `cobo login -u` → `cobo keys generate --key-type API` → `cobo keys register` |
| 401 / error_code 2024 | Key not registered | dev: `cobo keys register` / prod: `cobo open developer` |
| 403 / error_code 2025 | No Payment permission | `cobo open developer` → add Payment permissions to key |
| SSL certificate error | Corporate VPN certificate not trusted | Run `cobo login -u` manually — accept the certificate warning in the browser that opens |
| JSON response | Ready | Proceed with task |

> **VPN note:** On corporate VPN (e.g. Cloudflare), SSL certificate errors may block `cobo login -u`. Run it manually and accept the certificate prompt in the browser before proceeding.

## Before Generating API Requests

Always look up parameters before writing CLI commands or SDK code:
1. Identify the endpoint from user intent (e.g. "create order" → `POST /payments/orders`)
2. Run `cobo doc /payments/<path>` to read parameter names, types, and required/optional
3. Generate the exact CLI command or SDK call using those parameters
4. When comparing two similar objects (e.g. Counterparty vs Destination), run `cobo doc` on **both** endpoints before answering — do not rely solely on `references/concepts.md`

## Reference Navigation

| Task | Reference |
|------|-----------|
| All endpoint parameters | `references/api-quickref.md` |
| Business terminology | `references/concepts.md` |
| End-to-end workflows | `references/recipes.md` |
| Error codes & recovery | `references/errors.md` |
| SDK — Python | `assets/templates/python.md` |
| SDK — TypeScript / Node.js | `assets/templates/ts-node.md` |
| SDK — Go | `assets/templates/go.md` |
| SDK — Java | `assets/templates/java.md` |

## SDK Code Generation Rules

Uses the same `cobo_waas2` SDK as cobo-waas. Payment APIs are accessed via `PaymentApi`.

1. Minimal setup block + one short operation block per task — no wrapper functions, no extra classes
2. Use `PaymentApi` (not `WalletsApi`) for all `/payments/*` endpoints
3. Only pass parameters the task needs — never fill in every optional field
4. No custom DTOs, no forced serialization unless explicitly asked
5. Load the template for the target language from `assets/templates/<language>.md` and follow its style exactly

**Environment setup (all languages):**
```bash
eval $(cobo config env)   # macOS/Linux — load COBO_API_SECRET, COBO_ENV
```

## Recovery Patterns

When operations fail, **execute the fix automatically**. See `references/errors.md` for full error code tables, payment-specific issues, and recovery steps.

Short version: identify the error → diagnose → apply fix → re-run the original operation.

## Guardrails

- **Never echo** `COBO_API_SECRET` or private keys in output
- **Confirm environment** before write operations — production affects real funds
- **Idempotency**: always use unique `request_id` for orders, refunds, payouts
- **Never reuse** `request_id` — duplicates are rejected (error_code 30001)
- After each action, briefly report what happened (action, IDs, next step) — no rigid JSON schema required
