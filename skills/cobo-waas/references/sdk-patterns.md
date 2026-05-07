# SDK Patterns: Vibe Coding Guide

Guide for generating SDK code quickly. Helps agents translate CLI operations to SDK code.

## Code generation rules (must follow)
**Must be kept when generating code:** use the **template** of the corresponding language as the single source of truth. Template path: 'assets/templates/python.md', 'ts-node.md, 'go.md', 'java.md'. The code structure and style must be consistent with the template (Setup is used briefly for one operation). No additional encapsulation functions, no guessing parameters, and no forced serialization to dict/JSON are required unless explicitly requested by the user. For details, see SKILL.md "SDK Code Generation Specification 」.

## When to Use CLI vs SDK

| Scenario | Recommendation | Reason |
|----------|----------------|--------|
| Quick exploration | CLI | Faster iteration |
| One-off operations | CLI | No code needed |
| Automation scripts | SDK | Better error handling |
| Production services | SDK | Type safety, retries |
| Complex workflows | SDK | State management |
| Webhook handlers | SDK | Server integration |

**Rule of thumb**: Use CLI for exploration and testing, SDK for production code.

## Environment Setup Patterns

All SDKs should read configuration from environment variables for security.

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `COBO_API_SECRET` | Private key (hex string) |
| `COBO_API_KEY` | Public key (hex string, optional) |
| `COBO_ENV` | Environment: `dev`, `prod`, `sandbox` |
| `COBO_API_HOST` | Custom API host (optional) |

### Python Setup

```python
import os

# Required
api_secret = os.environ.get("COBO_API_SECRET")
if not api_secret:
    raise ValueError("COBO_API_SECRET not set")

# Optional with default
env = os.environ.get("COBO_ENV", "dev")
host_map = {
    "dev": "https://api.dev.cobo.com/v2",
    "prod": "https://api.cobo.com/v2",
    "sandbox": "https://api.sandbox.cobo.com/v2",
}
host = os.environ.get("COBO_API_HOST", host_map.get(env))
```

### Node.js Setup

```javascript
const apiSecret = process.env.COBO_API_SECRET;
if (!apiSecret) {
  throw new Error("COBO_API_SECRET not set");
}

const env = process.env.COBO_ENV || "dev";
```

### Go Setup

```go
apiSecret := os.Getenv("COBO_API_SECRET")
if apiSecret == "" {
    log.Fatal("COBO_API_SECRET not set")
}

env := os.Getenv("COBO_ENV")
if env == "" {
    env = "dev"
}
```

## CLI to SDK Translation

### List Wallets

**CLI:**
```bash
cobo get /wallets --wallet_type Custodial --limit 10
```

**Python:**
```python
from cobo_waas2.api import WalletsApi

wallets_api = WalletsApi(api_client)
response = wallets_api.list_wallets(
    wallet_type="Custodial",
    limit=10
)
for wallet in response.data:
    print(wallet.wallet_id, wallet.name)
```

**Node.js:**
```javascript
const walletsApi = new CoboWaas2.WalletsApi();
const response = await walletsApi.listWallets({
  walletType: "Custodial",
  limit: 10
});
response.data.forEach(wallet => {
  console.log(wallet.wallet_id, wallet.name);
});
```

### Create Custodial Wallet

**CLI:**
```bash
cobo post /wallets --wallet_type Custodial --wallet_subtype Asset --name "My Wallet"
```

**Python:**
```python
from cobo_waas2.models import CreateWalletParams, CreateCustodialWalletParams, WalletType, WalletSubtype

params = CreateWalletParams(actual_instance=CreateCustodialWalletParams(
    name="My Wallet",
    wallet_type=WalletType.CUSTODIAL,
    wallet_subtype=WalletSubtype.ASSET
))
response = wallets_api.create_wallet(create_wallet_params=params)
wallet = response.actual_instance
print(f"Created: {wallet.wallet_id}")
```

**Node.js:**
```javascript
const params = {
  name: "My Wallet",
  wallet_type: "Custodial",
  wallet_subtype: "Asset"
};
const wallet = await walletsApi.createWallet(params);
console.log(`Created: ${wallet.wallet_id}`);
```

### Create Address

**CLI:**
```bash
cobo post /wallets/{wallet_id}/addresses --chain_id ETH
```

**Python:**
```python
from cobo_waas2.models import CreateAddressRequest

response = wallets_api.create_address(
    wallet_id=wallet_id,
    create_address_request=CreateAddressRequest(chain_id="ETH", count=1)
)
address = response.data[0]  # Response is a list
print(f"Address: {address.address}")
```

### Create Transfer

**CLI:**
```bash
cobo post /transactions/transfer \
  --request_id "tx-123" \
  --source '{"source_type":"Wallet","wallet_id":"..."}' \
  --token_id "ETH" \
  --destination '{"destination_type":"Address","account_output":{"address":"0x...","amount":"0.01"}}'
```

**Python:**
```python
import time
import os
from cobo_waas2.api import TransactionsApi
from cobo_waas2.models import TransferParams, TransferSource, TransferDestination, WalletSubtype, CustodialTransferSource, AddressTransferDestination, AddressTransferDestinationAccountOutput

tx_api = TransactionsApi(api_client)

params = TransferParams(
    request_id=f"tx-{int(time.time())}-{os.urandom(4).hex()}",
    source=TransferSource(
        actual_instance=CustodialTransferSource(
            source_type=WalletSubtype.ASSET,
            wallet_id=wallet_id
        )
    ),
    token_id="ETH",
    destination=TransferDestination(
        actual_instance=AddressTransferDestination(
            destination_type="Address",
            account_output=AddressTransferDestinationAccountOutput(
                address="0x...",
                amount="0.01"
            )
        )
    )
)

response = tx_api.create_transfer_transaction(transfer_params=params)
tx = response.actual_instance
print(f"TX: {tx.transaction_id}, Status: {tx.status}")
```

### Get Transaction Status

**CLI:**
```bash
cobo get /transactions/{transaction_id}
```

**Python:**
```python
tx = transactions_api.get_transaction(transaction_id=transaction_id)
print(f"Status: {tx.status}")
```

## Error Handling Patterns

### Python

```python
from cobo_waas2.exceptions import ApiException

try:
    wallet = wallets_api.get_wallet_by_id(wallet_id="invalid")
except ApiException as e:
    print(f"Error {e.status}: {e.reason}")
    print(f"Body: {e.body}")

    if e.status == 401:
        print("Authentication failed - check API key")
    elif e.status == 404:
        print("Resource not found")
    elif e.status == 429:
        print("Rate limited - wait and retry")
```

### Node.js

```javascript
try {
  const wallet = await walletsApi.getWalletById("invalid");
} catch (error) {
  if (error.response) {
    console.log(`Error ${error.response.status}: ${error.response.statusText}`);
    console.log(`Body: ${JSON.stringify(error.response.data)}`);

    switch (error.response.status) {
      case 401:
        console.log("Authentication failed - check API key");
        break;
      case 404:
        console.log("Resource not found");
        break;
      case 429:
        console.log("Rate limited - wait and retry");
        break;
    }
  } else {
    console.log(`Network error: ${error.message}`);
  }
}
```

### Go

```go
wallet, _, err := client.WalletsAPI.GetWalletById(ctx, "invalid").Execute()
if err != nil {
    if apiErr, ok := err.(*cobo_waas2.GenericOpenAPIError); ok {
        fmt.Printf("Error: %s\n", apiErr.Error())
        fmt.Printf("Body: %s\n", string(apiErr.Body()))
    }
    return
}
```

## Async Patterns for Long Operations

Transactions can take time to complete. Use polling or webhooks.

### Polling Pattern (Python)

```python
import time

def wait_for_transaction(transaction_id, timeout=300, interval=10):
    """Poll until transaction reaches terminal state."""
    terminal_states = {"Completed", "Failed", "Rejected", "Cancelled"}
    start = time.time()

    while time.time() - start < timeout:
        tx = transactions_api.get_transaction(transaction_id=transaction_id)
        print(f"Status: {tx.status}")

        if tx.status in terminal_states:
            return tx

        time.sleep(interval)

    raise TimeoutError(f"Transaction {transaction_id} did not complete")

# Usage
tx = wait_for_transaction(transaction_id)
if tx.status == "Completed":
    print("Success!")
else:
    print(f"Failed: {tx.fail_reason}")
```

### Polling Pattern (Node.js)

```javascript
async function waitForTransaction(transactionId, timeout = 300000, interval = 10000) {
  const terminalStates = new Set(["Completed", "Failed", "Rejected", "Cancelled"]);
  const start = Date.now();

  while (Date.now() - start < timeout) {
    const tx = await transactionsApi.getTransaction(transactionId);
    console.log(`Status: ${tx.status}`);

    if (terminalStates.has(tx.status)) {
      return tx;
    }

    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(`Transaction ${transactionId} did not complete`);
}
```

## Webhook Handler Pattern

### Python (Flask)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = os.environ.get("COBO_WEBHOOK_SECRET")

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    # Verify signature
    signature = request.headers.get("X-Cobo-Signature")
    body = request.get_data()

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return jsonify({"error": "Invalid signature"}), 401

    # Process event
    event = request.json
    event_type = event.get("event_type")

    if event_type == "wallets.transaction.succeeded":
        tx_id = event["data"]["transaction_id"]
        print(f"Transaction {tx_id} completed")
        # Handle completion

    elif event_type == "wallets.transaction.failed":
        tx_id = event["data"]["transaction_id"]
        print(f"Transaction {tx_id} failed")
        # Handle failure

    return jsonify({"status": "ok"})
```

### Node.js (Express)

```javascript
const express = require("express");
const crypto = require("crypto");

const app = express();
app.use(express.json());

const WEBHOOK_SECRET = process.env.COBO_WEBHOOK_SECRET;

app.post("/webhook", (req, res) => {
  // Verify signature
  const signature = req.headers["x-cobo-signature"];
  const body = JSON.stringify(req.body);

  const expected = crypto
    .createHmac("sha256", WEBHOOK_SECRET)
    .update(body)
    .digest("hex");

  if (signature !== expected) {
    return res.status(401).json({ error: "Invalid signature" });
  }

  // Process event
  const { event_type, data } = req.body;

  switch (event_type) {
    case "wallets.transaction.succeeded":
      console.log(`Transaction ${data.transaction_id} completed`);
      break;
    case "wallets.transaction.failed":
      console.log(`Transaction ${data.transaction_id} failed`);
      break;
  }

  res.json({ status: "ok" });
});
```

## Common SDK Operations Matrix

| Operation | Python | Node.js | Go |
|-----------|--------|---------|-----|
| List wallets | `wallets_api.list_wallets()` | `walletsApi.listWallets()` | `client.WalletsAPI.ListWallets()` |
| Get wallet | `wallets_api.get_wallet_by_id(id)` | `walletsApi.getWalletById(id)` | `client.WalletsAPI.GetWalletById(id)` |
| Create wallet | `wallets_api.create_wallet(params)` | `walletsApi.createWallet(params)` | `client.WalletsAPI.CreateWallet(params)` |
| List addresses | `wallets_api.list_addresses(id)` | `walletsApi.listAddresses(id)` | `client.WalletsAPI.ListAddresses(id)` |
| Create address | `wallets_api.create_address(id, params)` | `walletsApi.createAddress(id, params)` | `client.WalletsAPI.CreateAddress(id, params)` |
| Create transfer | `transactions_api.create_transfer(params)` | `transactionsApi.createTransfer(params)` | `client.TransactionsAPI.CreateTransfer(params)` |
| Get transaction | `transactions_api.get_transaction(id)` | `transactionsApi.getTransaction(id)` | `client.TransactionsAPI.GetTransaction(id)` |

## SDK Reference Links

- **Python**: See `samples/python.md` for complete examples
- **Node.js**: See `samples/ts-node.md` for complete examples
- **Go**: See `samples/go.md` for complete examples
- **Java**: See `samples/java.md` for complete examples
