# JavaScript / Node.js SDK Sample (WaaS 2.0)

Complete Node.js/TypeScript SDK examples for Cobo WaaS 2.0 operations.

## Installation

```bash
npm install @cobo/cobo-waas2 --save
```

## Environment (all languages)

- **macOS / Linux:** `eval $(cobo config env)`
- **Windows PowerShell:** `cobo config env --format powershell | Invoke-Expression`
- **Windows CMD:** `cobo config env --format cmd > env.bat && env.bat`

## Configuration from Environment

```javascript
const CoboWaas2 = require("@cobo/cobo-waas2");

// Read from environment variables (recommended)
const apiSecret = process.env.COBO_API_SECRET;
if (!apiSecret) {
  throw new Error("COBO_API_SECRET environment variable not set");
}

const env = process.env.COBO_ENV || "dev";

// Initialize the API client
const apiClient = CoboWaas2.ApiClient.instance;
apiClient.setPrivateKey(apiSecret);

// Set environment
const envMap = {
  dev: CoboWaas2.Env.DEV,
  prod: CoboWaas2.Env.PROD,
  sandbox: CoboWaas2.Env.SANDBOX,
};
apiClient.setEnv(envMap[env] || CoboWaas2.Env.DEV);
```

### TypeScript Configuration

```typescript
import * as CoboWaas2 from "@cobo/cobo-waas2";

const apiSecret = process.env.COBO_API_SECRET;
if (!apiSecret) {
  throw new Error("COBO_API_SECRET environment variable not set");
}

const apiClient = CoboWaas2.ApiClient.instance;
apiClient.setPrivateKey(apiSecret);
apiClient.setEnv(CoboWaas2.Env.DEV);
```

## List Wallets

```javascript
const walletsApi = new CoboWaas2.WalletsApi();

// List all wallets
async function listWallets() {
  try {
    const response = await walletsApi.listWallets({ limit: 10 });
    console.log(`Found ${response.data.length} wallets`);

    response.data.forEach(wallet => {
      console.log(`  ${wallet.wallet_id}: ${wallet.name} (${wallet.wallet_type})`);
    });

    return response.data;
  } catch (error) {
    console.error("Error listing wallets:", error.message);
    throw error;
  }
}

// Filter by wallet type
async function listCustodialWallets() {
  const response = await walletsApi.listWallets({
    walletType: "Custodial",
    limit: 50
  });
  return response.data;
}

// Pagination
async function listAllWallets() {
  const allWallets = [];
  let after = null;

  while (true) {
    const response = await walletsApi.listWallets({ limit: 100, after });
    allWallets.push(...response.data);

    if (!response.pagination || !response.pagination.after) {
      break;
    }
    after = response.pagination.after;
  }

  return allWallets;
}
```

## Create Custodial Wallet

```javascript
async function createCustodialWallet(name) {
  const params = {
    name: name,
    wallet_type: "Custodial",
    wallet_subtype: "Asset"
  };

  try {
    const wallet = await walletsApi.createWallet(params);
    console.log(`Created wallet: ${wallet.wallet_id}`);
    console.log(`  Name: ${wallet.name}`);
    console.log(`  Type: ${wallet.wallet_type}/${wallet.wallet_subtype}`);
    return wallet;
  } catch (error) {
    console.error("Error creating wallet:", error.message);
    throw error;
  }
}
```

## Create MPC Org-Controlled Wallet

```javascript
async function createMpcWallet(name, vaultId) {
  const params = {
    name: name,
    wallet_type: "MPC",
    wallet_subtype: "Org-Controlled",
    vault_id: vaultId
  };

  try {
    const wallet = await walletsApi.createWallet(params);
    console.log(`Created MPC wallet: ${wallet.wallet_id}`);
    return wallet;
  } catch (error) {
    console.error("Error creating MPC wallet:", error.message);
    throw error;
  }
}

// Get vault_id first
async function getVaultId() {
  // Using raw API call for vaults
  const response = await apiClient.callApi(
    "/vaults",
    "GET",
    {},
    {},
    {},
    {},
    null,
    [],
    ["application/json"],
    ["application/json"]
  );
  return response.data[0].vault_id;
}
```

## Create Address

```javascript
async function createAddress(walletId, chainId = "ETH") {
  try {
    // Get supported chains
    const chains = await walletsApi.listSupportedChains(walletId);
    console.log(`Supported chains: ${chains.data.map(c => c.chain_id).join(", ")}`);

    // Create address
    const address = await walletsApi.createAddress(walletId, { chain_id: chainId });
    console.log(`Created address: ${address.address}`);
    console.log(`  Chain: ${address.chain_id}`);
    console.log(`  Address ID: ${address.address_id}`);

    return address;
  } catch (error) {
    console.error("Error creating address:", error.message);
    throw error;
  }
}
```

## Create Transfer

```javascript
const transactionsApi = new CoboWaas2.TransactionsApi();

async function createTransfer(sourceWalletId, destinationAddress, tokenId, amount) {
  // Validate destination first
  const validation = await walletsApi.checkAddressValidity({
    chainId: tokenId.split("_")[0] || tokenId,
    address: destinationAddress
  });

  if (!validation.is_valid) {
    throw new Error(`Invalid address: ${validation.message}`);
  }

  // Create unique request_id
  const requestId = `tx-${Date.now()}-${Math.random().toString(36).substr(2, 8)}`;

  const params = {
    request_id: requestId,
    source: {
      source_type: "Wallet",
      wallet_id: sourceWalletId
    },
    token_id: tokenId,
    destination: {
      destination_type: "Address",
      address: destinationAddress,
      amount: amount
    }
  };

  try {
    const transaction = await transactionsApi.createTransfer(params);
    console.log(`Created transaction: ${transaction.transaction_id}`);
    console.log(`  Status: ${transaction.status}`);
    console.log(`  Request ID: ${transaction.request_id}`);
    return transaction;
  } catch (error) {
    console.error("Error creating transfer:", error.message);
    throw error;
  }
}
```

## Check Transaction Status

```javascript
async function getTransactionStatus(transactionId) {
  const tx = await transactionsApi.getTransaction(transactionId);
  console.log(`Transaction ${tx.transaction_id}`);
  console.log(`  Status: ${tx.status}`);
  console.log(`  Token: ${tx.token_id}`);
  console.log(`  Created: ${tx.created_timestamp}`);
  return tx;
}

// Poll until complete
async function waitForCompletion(transactionId, timeout = 300000, interval = 10000) {
  const terminalStates = new Set(["Completed", "Failed", "Rejected", "Cancelled"]);
  const start = Date.now();

  while (Date.now() - start < timeout) {
    const tx = await transactionsApi.getTransaction(transactionId);
    console.log(`  Status: ${tx.status}`);

    if (terminalStates.has(tx.status)) {
      return tx;
    }

    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(`Transaction ${transactionId} did not complete in ${timeout}ms`);
}

// Usage
async function executeAndWait() {
  const tx = await createTransfer(
    "wallet_id",
    "0x742d35Cc...",
    "ETH",
    "0.01"
  );

  const finalTx = await waitForCompletion(tx.transaction_id);

  if (finalTx.status === "Completed") {
    console.log(`Success! TX hash: ${finalTx.transaction_hash}`);
  } else {
    console.log(`Failed: ${finalTx.fail_reason}`);
  }
}
```

## Error Handling

```javascript
async function safeApiCall(apiFunc, ...args) {
  const maxRetries = 3;
  let retryDelay = 1000;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await apiFunc(...args);

    } catch (error) {
      const status = error.response?.status;
      console.log(`API Error ${status}: ${error.message}`);

      if (status === 401) {
        throw new Error("Authentication failed - check COBO_API_SECRET");
      }

      if (status === 403) {
        throw new Error("Permission denied - check API key permissions");
      }

      if (status === 404) {
        throw new Error(`Resource not found: ${error.response?.data}`);
      }

      if (status === 429) {
        // Rate limited - wait and retry
        const waitTime = retryDelay * Math.pow(2, attempt);
        console.log(`Rate limited, waiting ${waitTime}ms...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
        continue;
      }

      if (status >= 500) {
        // Server error - retry
        if (attempt < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          continue;
        }
      }

      throw error;
    }
  }

  throw new Error(`Failed after ${maxRetries} attempts`);
}

// Usage
try {
  const wallet = await safeApiCall(
    () => walletsApi.getWalletById("wallet_id")
  );
} catch (error) {
  console.error(`Error: ${error.message}`);
}
```

## Complete Example Script

```javascript
#!/usr/bin/env node
/**
 * Complete Cobo WaaS 2.0 workflow example for Node.js
 */

const CoboWaas2 = require("@cobo/cobo-waas2");

async function main() {
  // Setup
  const apiSecret = process.env.COBO_API_SECRET;
  if (!apiSecret) {
    throw new Error("Set COBO_API_SECRET environment variable");
  }

  const env = process.env.COBO_ENV || "dev";

  const apiClient = CoboWaas2.ApiClient.instance;
  apiClient.setPrivateKey(apiSecret);

  const envMap = {
    dev: CoboWaas2.Env.DEV,
    prod: CoboWaas2.Env.PROD,
  };
  apiClient.setEnv(envMap[env] || CoboWaas2.Env.DEV);

  const walletsApi = new CoboWaas2.WalletsApi();
  const transactionsApi = new CoboWaas2.TransactionsApi();

  // List existing wallets
  console.log("Listing wallets...");
  const wallets = await walletsApi.listWallets({
    walletType: "Custodial",
    limit: 10
  });

  wallets.data.forEach(w => {
    console.log(`  ${w.name}: ${w.wallet_id}`);
  });

  // Create wallet if none exist
  let wallet;
  if (wallets.data.length === 0) {
    console.log("\nCreating wallet...");
    wallet = await walletsApi.createWallet({
      name: `Test Wallet ${Date.now()}`,
      wallet_type: "Custodial",
      wallet_subtype: "Asset"
    });
    console.log(`Created: ${wallet.wallet_id}`);
  } else {
    wallet = wallets.data[0];
  }

  // Create address
  console.log(`\nCreating address for wallet ${wallet.wallet_id}...`);
  try {
    const address = await walletsApi.createAddress(
      wallet.wallet_id,
      { chain_id: "ETH" }
    );
    console.log(`Address: ${address.address}`);
  } catch (error) {
    if (error.response?.status === 400) {
      console.log("Address may already exist, listing...");
      const addresses = await walletsApi.listAddresses(wallet.wallet_id);
      addresses.data.forEach(addr => {
        console.log(`  ${addr.chain_id}: ${addr.address}`);
      });
    } else {
      throw error;
    }
  }

  console.log("\nDone!");
}

main().catch(error => {
  console.error("Fatal error:", error.message);
  process.exit(1);
});
```

## TypeScript Complete Example

```typescript
#!/usr/bin/env ts-node
/**
 * Complete Cobo WaaS 2.0 workflow example for TypeScript
 */

import * as CoboWaas2 from "@cobo/cobo-waas2";

async function main(): Promise<void> {
  const apiSecret = process.env.COBO_API_SECRET;
  if (!apiSecret) {
    throw new Error("Set COBO_API_SECRET environment variable");
  }

  const apiClient = CoboWaas2.ApiClient.instance;
  apiClient.setPrivateKey(apiSecret);
  apiClient.setEnv(CoboWaas2.Env.DEV);

  const walletsApi = new CoboWaas2.WalletsApi();

  // List wallets with type safety
  const response = await walletsApi.listWallets({ limit: 10 });

  response.data.forEach((wallet: CoboWaas2.Wallet) => {
    console.log(`${wallet.wallet_id}: ${wallet.name}`);
  });
}

main().catch(console.error);
```

## Environment Setup

```bash
# Set environment variables
export COBO_API_SECRET="<your-64-char-hex-secret>"
export COBO_ENV="dev"

# Run JavaScript
node example.js

# Run TypeScript
npx ts-node example.ts
```

## Package.json Example

```json
{
  "name": "cobo-waas-example",
  "version": "1.0.0",
  "scripts": {
    "start": "node example.js",
    "start:ts": "ts-node example.ts"
  },
  "dependencies": {
    "@cobo/cobo-waas2": "^1.0.0"
  },
  "devDependencies": {
    "@types/node": "^18.0.0",
    "ts-node": "^10.9.0",
    "typescript": "^5.0.0"
  }
}
```
