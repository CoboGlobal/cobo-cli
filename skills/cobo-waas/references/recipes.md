# Recipes: End-to-End Workflows

Complete workflows for common Cobo WaaS tasks. Each recipe includes prerequisites, steps, permissions, and verification.

## Permissions Quick Reference

| Recipe | Required Permissions                                   |
|--------|--------------------------------------------------------|
| 1. First API Call | Wallet - Read                                          |
| 2. Custodial Wallet | Wallet - Read/Write, Address - Read/Write              |
| 3. MPC Wallet | Wallet - Read/Write, Address - Write, MPC Vault - Read |
| 4. Transfer | Transaction - Write, Wallet - Read                     |
| 5. Monitor TX | Transaction - Read                                     |
| 6. Debug TX | Transaction - Read, Wallet - Read                      |
| 7. Webhooks | Webhook - Read/Write                                        |

Configure permissions: `cobo open developer` → Edit API Key → Permissions

---

## Recipe 1: First API Call

Minimal path from fresh install to successful API call.

### Prerequisites
- Python 3.8+
- Internet connection

### Steps

```bash
# 1. Install CLI
pip install cobo-cli

# 2. Verify installation
cobo version

# 3. Set environment (dev for testing)
cobo env dev

# 4. Generate API keys
cobo keys generate --key-type API
# SAVE THE OUTPUT - secret shown only once!

# 5. Register key in Portal
cobo open developer
# In Portal: Developer Console → API Keys → Add Key
# Paste the PUBLIC key, select permissions, save

# 6. Set auth method
cobo auth apikey

# 7. Verify setup
cobo config list

# 8. Make first API call
cobo get /wallets --limit 1
```

### Expected Output
```json
{
  "data": [],
  "pagination": { ... }
}
```

### Verification
- No errors
- JSON response (even if empty data array)

---

## Recipe 2: Create Custodial Wallet and Address

Create a Custodial wallet and generate an address for deposits.

### Prerequisites
- Completed Recipe 1 (working API auth)

### Permissions Required
- Wallet - Read, Write
- Address - Write

### Steps

**Tip:** Before building the request, run `cobo doc /wallets` to see exact parameter names and types for this endpoint.

```bash
# 1. Create Custodial Asset wallet
cobo post /wallets \
  --wallet_type Custodial \
  --wallet_subtype Asset \
  --name "My Treasury Wallet"

# Response includes wallet_id - save it!
# Example: "wallet_id": "f47ac10b-58cc-..."
```

```bash
# 2. Store wallet_id
WALLET_ID="<wallet_id_from_response>"

# 3. Check supported chains for this wallet (IMPORTANT!)
cobo get /wallets/$WALLET_ID/chains
# Dev/Sandbox: Custodial uses COBO_ETH, not ETH
# Production: Uses standard chain IDs (ETH, BTC, etc.)

# 4. Create an address (use correct chain_id for your environment)
cobo post /wallets/$WALLET_ID/addresses \
  --chain_id COBO_ETH  \  # For dev/sandbox
  # --chain_id ETH     \  # For production
  --count 1

# Response includes address and address_id

# 5. Verify address was created
cobo get /wallets/$WALLET_ID/addresses
```

### Expected Output

Wallet creation:
```json
{
  "wallet_id": "f47ac10b-...",
  "wallet_type": "Custodial",
  "wallet_subtype": "Asset",
  "name": "My Treasury Wallet"
}
```

Address creation:
```json
{
  "address_id": "abc123...",
  "address": "0x1234...",
  "chain_id": "ETH"
}
```

### Verification
```bash
# List wallets - should include new wallet
cobo get /wallets --wallet_type Custodial

# List addresses - should include new address
cobo get /wallets/$WALLET_ID/addresses
```

---

## Recipe 3: Create MPC Org-Controlled Wallet

Create an MPC wallet with organization control.

### Prerequisites
- Completed Recipe 1
- MPC vault exists (created in Portal)

### Permissions Required
- Wallet - Read, Write
- Address - Write
- MPC Vault - Read

### Steps

```bash
# 1. List available vaults (NOTE: endpoint is /wallets/mpc/vaults, not /vaults)
cobo get /wallets/mpc/vaults

# Save vault_id from response
VAULT_ID="<vault_id_from_response>"

# 2. Create MPC Org-Controlled wallet
cobo post /wallets \
  --wallet_type MPC \
  --wallet_subtype Org-Controlled \
  --name "MPC Treasury" \
  --vault_id $VAULT_ID

# Save wallet_id
WALLET_ID="<wallet_id_from_response>"

# 3. Check supported chains (IMPORTANT!)
cobo get /wallets/$WALLET_ID/chains
# Dev/Sandbox: MPC uses ANVIL_SETH (Sepolia), not ETH
# Production: Uses standard chain IDs

# 4. Create address (use correct chain_id for your environment)
cobo post /wallets/$WALLET_ID/addresses \
  --chain_id ANVIL_SETH \  # For dev/sandbox
  # --chain_id ETH      \  # For production
  --count 1

# 5. Verify
cobo get /wallets/$WALLET_ID
cobo get /wallets/$WALLET_ID/addresses
```

### Common Issues

**Vault not found (404 on /vaults):**
- Use `/wallets/mpc/vaults`, not `/vaults`

**No vaults returned:**
1. Open Portal: `cobo open portal`
2. Navigate to MPC Wallets → Vaults
3. Create a new vault or use existing

**Chain not enabled:**
- Check supported chains with `cobo get /wallets/wallets/enabled_chains --wallet_type MPC`
- MPC wallets in dev/sandbox typically use `ANVIL_SETH`

---

## Recipe 4: Execute a Transfer

Transfer tokens from one address to another.

### Prerequisites
- Source wallet with funds
- Destination address
- Working API auth

### Permissions Required
- Transaction - Write
- Wallet - Read

> **Note**: The CLI has limitations with complex JSON bodies. For production automation, consider using the SDK instead (see `references/samples/python.md`).

### Steps

```bash
# 1. Set variables
SOURCE_WALLET_ID="<your_wallet_id>"
DESTINATION_ADDRESS="0x..."
TOKEN_ID="ETH"
AMOUNT="0.01"

# 2. Check source wallet balance
cobo get /wallets/$SOURCE_WALLET_ID/token_balances

# 3. Validate destination address
cobo get /wallets/check_address_validity \
  --chain_id ETH \
  --address $DESTINATION_ADDRESS

# 4. Estimate fees
cobo post /transactions/estimate_fee \
  --request_id "fee-$(date +%s)" \
  --source "{\"source_type\":\"Asset\",\"wallet_id\":\"$SOURCE_WALLET_ID\"}" \
  --token_id $TOKEN_ID \
  --destination "{\"destination_type\":\"Address\",\"account_output\":{\"address\":\"$DESTINATION_ADDRESS\",\"amount\":\"$AMOUNT\"}}"

# 5. Create transfer with unique request_id
REQUEST_ID="tx-$(date +%s)-$(openssl rand -hex 4)"

cobo post /transactions/transfer \
  --request_id $REQUEST_ID \
  --source "{\"source_type\":\"Asset\",\"wallet_id\":\"$SOURCE_WALLET_ID\"}" \
  --token_id $TOKEN_ID \
  --destination "{\"destination_type\":\"Address\",\"account_output\":{\"address\":\"$DESTINATION_ADDRESS\",\"amount\":\"$AMOUNT\"}}"

# Save transaction_id from response
TRANSACTION_ID="<transaction_id_from_response>"

# 6. Check status
cobo get /transactions/$TRANSACTION_ID
```

### Transaction States
Use [Transaction Statuses](https://www.cobo.com/developers/v2/guides/transactions/status.md) - primary reference for transaction statuses

### Common Issues

**Insufficient balance:**
```bash
cobo get /wallets/$SOURCE_WALLET_ID/token_balances
# Ensure balance > amount + estimated fee
```

**Pending authorization:**
```bash
# Open Portal to approve
cobo open portal
# Navigate to Transactions → Pending
```

---

## Recipe 5: Monitor Transaction Status

Poll for transaction completion.

### Prerequisites
- Active transaction_id

### Steps

```bash
TRANSACTION_ID="<your_transaction_id>"

# Single status check
cobo get /transactions/$TRANSACTION_ID

# Polling script
while true; do
  STATUS=$(cobo get /transactions/$TRANSACTION_ID | jq -r '.status')
  echo "Status: $STATUS"

  if [[ "$STATUS" == "Completed" || "$STATUS" == "Failed" || "$STATUS" == "Rejected" ]]; then
    echo "Transaction finished with status: $STATUS"
    break
  fi

  sleep 10
done

# Get full transaction details after completion
cobo get /transactions/$TRANSACTION_ID
```

### Alternative: Webhooks

Instead of polling, set up webhooks:

```bash
# 1. Create webhook endpoint
cobo post /webhooks/endpoints \
  --url "https://your-server.com/webhook" \
  --events '["wallets.transaction.succeeded","wallets.transaction.failed"]'

# 2. Listen for events (for testing)
cobo webhook listen --events "transaction.completed"
```

---

## Recipe 6: Debug a Failed Transaction

Diagnose why a transaction failed.

### Prerequisites
- Failed transaction_id

### Steps

```bash
TRANSACTION_ID="<failed_transaction_id>"

# 1. Get full transaction details
cobo get /transactions/$TRANSACTION_ID

# Look for:
# - status: "Failed" or "Rejected"
# - fail_reason: explains the failure
# - sub_status: more detail

# 2. Check common causes

# Insufficient balance?
WALLET_ID=$(cobo get /transactions/$TRANSACTION_ID | jq -r '.source.wallet_id')
cobo get /wallets/$WALLET_ID/token_balances

# Invalid destination?
DEST_ADDRESS=$(cobo get /transactions/$TRANSACTION_ID | jq -r '.destination.address')
CHAIN_ID=$(cobo get /transactions/$TRANSACTION_ID | jq -r '.chain_id')
cobo get /wallets/check_address_validity --chain_id $CHAIN_ID --address $DEST_ADDRESS

# 3. Check API logs
cobo logs tail

# 4. Enable debug for more details
cobo --enable-debug get /transactions/$TRANSACTION_ID
```

### Common Failure Reasons

| Reason | Cause | Fix |
|--------|-------|-----|
| `insufficient_balance` | Not enough funds | Fund wallet |
| `invalid_address` | Bad destination | Validate address |
| `policy_rejected` | Risk policy blocked | Review in Portal |
| `signing_failed` | MPC signing issue | Check MPC setup |

---

## Recipe 7: Set Up Webhook Listener

Receive real-time notifications for events.

### Prerequisites
- Working API auth
- Publicly accessible URL (for production) or local listener (for testing)

### Permissions Required
- Webhook - Read

### Steps

#### For Testing (Local Listener)

```bash
# 1. Start local webhook listener
cobo webhook listen --events "wallets.transaction.succeeded,wallets.transaction.failed"

# This creates a temporary tunnel and registers the webhook

# 2. Trigger a test event
cobo webhook trigger wallets.transaction.succeeded

# 3. Observe the event in the listener output
```

#### For Production

```bash
# 1. List available event types
cobo webhook events
# Or via API: cobo get /webhooks/event_definitions

# 2. Create webhook endpoint
cobo post /webhooks/endpoints \
  --url "https://your-server.com/webhook" \
  --events '["wallets.transaction.created","wallets.transaction.succeeded","wallets.transaction.failed"]'

# Save endpoint_id
ENDPOINT_ID="<endpoint_id_from_response>"

# 3. Verify endpoint
cobo get /webhooks/endpoints/$ENDPOINT_ID

# 4. Test with a transaction
# (perform a transfer and watch for webhook)
```

### Webhook Payload Example

```json
{
  "event_type": "wallets.transaction.succeeded",
  "event_id": "evt_...",
  "created_timestamp": 1234567890,
  "data": {
    "transaction_id": "...",
    "wallet_id": "...",
    "status": "Completed"
  }
}
```

## Quick Reference Table

| Task | Recipe |
|------|--------|
| First-time setup | Recipe 1 |
| Create Custodial wallet | Recipe 2 |
| Create MPC wallet | Recipe 3 |
| Transfer tokens | Recipe 4 |
| Monitor transaction | Recipe 5 |
| Debug failure | Recipe 6 |
| Set up webhooks | Recipe 7 |
