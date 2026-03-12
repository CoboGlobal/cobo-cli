# Concepts and Glossary

Quick reference for Cobo-specific terminology and concepts.

## Wallet Types

### Custodial Wallets

Cobo manages the private keys. Simplest to set up and use.

| Subtype | Description | Use Case |
|---------|-------------|----------|
| `Asset` | Standard asset custody | Treasury, holding |
| `Web3` | Web3 interaction enabled | DeFi, NFTs, dApps |

**Create Custodial wallet:**
```bash
cobo post /wallets \
  --wallet_type Custodial \
  --wallet_subtype Asset \
  --name "Treasury Wallet"
```

### MPC Wallets

Multi-Party Computation. Private key is split across multiple parties.

| Subtype | Description | Key Shares |
|---------|-------------|------------|
| `Org-Controlled` | Organization controls all shares | Cobo + Organization |
| `User-Controlled` | End users hold their shares | Cobo + User + (Optional) Organization |

**Create MPC Org-Controlled wallet:**
```bash
cobo post /wallets \
  --wallet_type MPC \
  --wallet_subtype Org-Controlled \
  --name "MPC Treasury" \
  --vault_id "<vault_id>"
```

## Auth Methods

| Method | CLI Command | Description | Use Case |
|--------|-------------|-------------|----------|
| `apikey` | `cobo auth apikey` | API key authentication | Automation, scripts, CI/CD |
| `user` | `cobo auth user` | User token from Portal login | Interactive Portal access |
| `org` | `cobo auth org` | Organization token | Portal apps (Cobo Apps) |
| `none` | `cobo auth none` | No authentication | Public endpoints only |

### API Key Authentication

1. Generate keypair: `cobo keys generate --key-type API`
2. Register public key in Portal Developer Console
3. CLI uses private key to sign requests

### User Authentication

1. Login: `cobo login --user`
2. Opens browser for Portal authentication
3. Token stored locally

## Environments

| Environment | Host | CLI Command | Use Case |
|-------------|------|-------------|----------|
| Sandbox | `api.sandbox.cobo.com` | `cobo env sandbox` | Isolated testing |
| Development | `api.dev.cobo.com` | `cobo env dev` | Development with test assets |
| Production | `api.cobo.com` | `cobo env prod` | Real assets |

**Important**: API keys are environment-specific. A key registered in `dev` won't work in `prod`.

## Common IDs

### wallet_id

Unique identifier for a wallet.

- Format: UUID (e.g., `f47ac10b-58cc-4372-a567-0e02b2c3d479`)
- Scope: Environment-specific
- Get via: `cobo get /wallets`

### transaction_id

Unique identifier for a transaction.

- Format: UUID
- Scope: Environment-specific
- Get via: `cobo get /transactions` or returned on creation

### request_id

Client-provided idempotency key for transactions.

- Format: String (you define it)
- Purpose: Prevents duplicate transactions
- Best practice: Include timestamp: `tx-$(date +%s)-$(openssl rand -hex 4)`

### chain_id

Blockchain network identifier.

> **Important**: Chain availability differs by wallet type and environment. Always check supported/enabled chains first:
> ```bash
> cobo get /wallets/chains --wallet_type Custodial
> ```

Using following command to get enabled chains
> ```bash
> cobo get /wallets/enabled_chains --wallet_type Custodial
> `
> 

### token_id

Token identifier combining chain and token.

> **Important**: Token availability differs by wallet type and environment. Always check supported/enabled tokens first:

Using following command to get supported chains
> ```bash
> cobo get /wallets/tokens --wallet_type Custodial
> ```

Using following command to get enabled chains
> ```bash
> cobo get /wallets/enabled_tokens --wallet_type Custodial
> `


### vault_id

MPC vault identifier (for MPC wallets only).

- Required when creating MPC wallets
- Get via: `cobo get /wallets/mpc/vaults --vault_type Org-Controlled` (not `/vaults`)

### address_id

Address identifier within a wallet.

- Get via: `cobo get /wallets/{wallet_id}/addresses`

## Transaction Lifecycle

- Use [Transaction Statuses](https://www.cobo.com/developers/v2/guides/transactions/status.md) - primary reference for transaction statuses
- Use [Custodial Wallets Transaction Flow](https://www.cobo.com/developers/v2/guides/transactions/transaction-process-custodial.md) - primary reference for transaction status flow for Custodial Wallets (Asset Wallets)
- Use [MPC and Web3 Wallets Transaction Flow](https://www.cobo.com/developers/v2/guides/transactions/transaction-process-mpc.md) - primary reference for transaction status flow for MPC Wallets and Web3 Wallets

### Transaction Types, Sources and Destinations
Use [Transaction Types, Sources and Destinations](https://www.cobo.com/developers/v2/guides/transactions/sources-and-destinations.md) as the primary reference.

## Fees

### Fee Levels

| Level | Description |
|-------|-------------|
| `Slow` | Lower fee, longer confirmation |
| `Average` | Standard fee and time |
| `Fast` | Higher fee, faster confirmation |

### Fee Estimation

Use [Fee Estimation](https://www.cobo.com/developers/v2/guides/transactions/estimate-fees.md) as the primary reference.

```bash
cobo post /transactions/estimate_fee \
  --request_id "fee-estimate-1" \
  --source '{"source_type":"Wallet","wallet_id":"..."}' \
  --token_id "ETH" \
  --destination '{"destination_type":"Address","address":"...","amount":"0.01"}'
```

## Webhooks

Use [Webhook Event Type](https://www.cobo.com/developers/v2/guides/webhooks-callbacks/webhook-event-type.md) as the primary reference.

### Webhook Flow

1. Configure endpoint: `cobo post /webhooks/endpoints --url "..." --events "[...]"`
2. Cobo sends POST with event data
3. Your endpoint returns 200 OK
4. Cobo retries on failure

## API Versioning

Current version: v2 (WaaS 2.0)

Base URLs:
- Dev: `https://api.dev.cobo.com/v2`
- Prod: `https://api.cobo.com/v2`
- Sandbox: `https://api.sandbox.cobo.com/v2`

## Pagination

| Parameter | Description |
|-----------|-------------|
| `limit` | Items per page (1-100, default 10) |
| `before` | Cursor for previous page |
| `after` | Cursor for next page |

Response includes pagination info:
```json
{
  "data": [...],
  "pagination": {
    "before": "cursor_prev",
    "after": "cursor_next",
    "total_count": 100
  }
}
```
