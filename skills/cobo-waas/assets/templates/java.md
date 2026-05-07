# Java SDK Sample (WaaS 2.0)

Complete Java SDK examples for Cobo WaaS 2.0 operations.

## Installation

### Maven

```xml
<dependency>
  <groupId>com.cobo.waas2</groupId>
  <artifactId>cobo-waas2</artifactId>
  <version>1.0.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'com.cobo.waas2:cobo-waas2:1.0.0'
```

## Environment (all languages)

- **macOS / Linux:** `eval $(cobo config env)`
- **Windows PowerShell:** `cobo config env --format powershell | Invoke-Expression`
- **Windows CMD:** `cobo config env --format cmd > env.bat && env.bat`

## Configuration from Environment

```java
import com.cobo.waas2.ApiClient;
import com.cobo.waas2.Configuration;
import com.cobo.waas2.Env;

public class CoboConfig {
    public static ApiClient getApiClient() {
        // Read from environment variables (recommended)
        String apiSecret = System.getenv("COBO_API_SECRET");
        if (apiSecret == null || apiSecret.isEmpty()) {
            throw new RuntimeException("COBO_API_SECRET environment variable not set");
        }

        String envStr = System.getenv("COBO_ENV");
        if (envStr == null || envStr.isEmpty()) {
            envStr = "dev";
        }

        // Get default client and configure
        ApiClient client = Configuration.getDefaultApiClient();
        client.setPrivKey(apiSecret);

        // Set environment
        Env env;
        switch (envStr.toLowerCase()) {
            case "prod":
                env = Env.PROD;
                break;
            case "sandbox":
                env = Env.SANDBOX;
                break;
            default:
                env = Env.DEV;
        }
        client.setEnv(env);

        return client;
    }
}
```

## List Wallets

```java
import com.cobo.waas2.api.WalletsApi;
import com.cobo.waas2.model.ListWallets200Response;
import com.cobo.waas2.model.WalletInfo;
import com.cobo.waas2.model.WalletType;

public class ListWalletsExample {
    public static void listWallets(ApiClient client) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            // List all wallets
            ListWallets200Response response = walletsApi.listWallets(
                null,  // walletType
                null,  // walletSubtype
                null,  // projectId
                null,  // vaultId
                10,    // limit
                null,  // before
                null   // after
            );

            System.out.println("Found " + response.getData().size() + " wallets");
            for (WalletInfo wallet : response.getData()) {
                System.out.printf("  %s: %s (%s)%n",
                    wallet.getWalletId(),
                    wallet.getName(),
                    wallet.getWalletType());
            }
        } catch (Exception e) {
            System.err.println("Error listing wallets: " + e.getMessage());
        }
    }

    // Filter by wallet type
    public static void listCustodialWallets(ApiClient client) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            ListWallets200Response response = walletsApi.listWallets(
                WalletType.CUSTODIAL,
                null,  // walletSubtype
                null,  // projectId
                null,  // vaultId
                50,    // limit
                null,  // before
                null   // after
            );

            for (WalletInfo wallet : response.getData()) {
                System.out.printf("%s: %s%n", wallet.getWalletId(), wallet.getName());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    // Pagination
    public static List<WalletInfo> listAllWallets(ApiClient client) {
        WalletsApi walletsApi = new WalletsApi(client);
        List<WalletInfo> allWallets = new ArrayList<>();
        String after = null;

        while (true) {
            try {
                ListWallets200Response response = walletsApi.listWallets(
                    null, null, null, null, 100, null, after
                );

                allWallets.addAll(response.getData());

                if (response.getPagination() == null ||
                    response.getPagination().getAfter() == null) {
                    break;
                }
                after = response.getPagination().getAfter();
            } catch (Exception e) {
                break;
            }
        }

        return allWallets;
    }
}
```

## Create Custodial Wallet

```java
import com.cobo.waas2.api.WalletsApi;
import com.cobo.waas2.model.CreateWalletParams;
import com.cobo.waas2.model.CreateCustodialWalletParams;
import com.cobo.waas2.model.CreatedWalletInfo;
import com.cobo.waas2.model.WalletType;
import com.cobo.waas2.model.WalletSubtype;

public class CreateWalletExample {
    public static CreatedWalletInfo createCustodialWallet(ApiClient client, String name) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            CreateCustodialWalletParams custodialParams = new CreateCustodialWalletParams();
            custodialParams.setName(name);
            custodialParams.setWalletType(WalletType.CUSTODIAL);
            custodialParams.setWalletSubtype(WalletSubtype.ASSET);

            CreateWalletParams params = new CreateWalletParams(custodialParams);

            CreatedWalletInfo wallet = walletsApi.createWallet(params);

            System.out.println("Created wallet: " + wallet.getWalletId());
            System.out.println("  Name: " + wallet.getName());
            System.out.println("  Type: " + wallet.getWalletType() + "/" + wallet.getWalletSubtype());

            return wallet;
        } catch (Exception e) {
            System.err.println("Error creating wallet: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
```

## Create MPC Org-Controlled Wallet

```java
import com.cobo.waas2.model.CreateMpcWalletParams;

public class CreateMpcWalletExample {
    public static CreatedWalletInfo createMpcWallet(ApiClient client, String name, String vaultId) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            CreateMpcWalletParams mpcParams = new CreateMpcWalletParams();
            mpcParams.setName(name);
            mpcParams.setWalletType(WalletType.MPC);
            mpcParams.setWalletSubtype(WalletSubtype.ORG_CONTROLLED);
            mpcParams.setVaultId(vaultId);

            CreateWalletParams params = new CreateWalletParams(mpcParams);

            CreatedWalletInfo wallet = walletsApi.createWallet(params);

            System.out.println("Created MPC wallet: " + wallet.getWalletId());
            return wallet;
        } catch (Exception e) {
            System.err.println("Error creating MPC wallet: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }

    // Get vault_id first
    public static String getVaultId(ApiClient client) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            var response = walletsApi.listMpcVaults(null, null, null);
            if (response.getData().isEmpty()) {
                throw new RuntimeException("No vaults found");
            }
            return response.getData().get(0).getVaultId();
        } catch (Exception e) {
            throw new RuntimeException("Error getting vault: " + e.getMessage());
        }
    }
}
```

## Create Address

```java
import com.cobo.waas2.model.AddressInfo;
import com.cobo.waas2.model.CreateAddressRequest;

public class CreateAddressExample {
    public static AddressInfo createAddress(ApiClient client, String walletId, String chainId) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            // Get supported chains
            var chains = walletsApi.listSupportedChains(walletId, null, null, null);
            System.out.print("Supported chains: ");
            for (var chain : chains.getData()) {
                System.out.print(chain.getChainId() + " ");
            }
            System.out.println();

            // Create address
            CreateAddressRequest request = new CreateAddressRequest();
            request.setChainId(chainId);

            AddressInfo address = walletsApi.createAddress(walletId, request);

            System.out.println("Created address: " + address.getAddress());
            System.out.println("  Chain: " + address.getChainId());
            System.out.println("  Address ID: " + address.getAddressId());

            return address;
        } catch (Exception e) {
            System.err.println("Error creating address: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
```

## Create Transfer

```java
import com.cobo.waas2.api.TransactionsApi;
import com.cobo.waas2.model.TransferParams;
import com.cobo.waas2.model.TransferSource;
import com.cobo.waas2.model.TransferDestination;
import com.cobo.waas2.model.WalletTransferSource;
import com.cobo.waas2.model.AddressTransferDestination;
import com.cobo.waas2.model.TransferResult;
import java.util.UUID;

public class CreateTransferExample {
    public static TransferResult createTransfer(
            ApiClient client,
            String sourceWalletId,
            String destinationAddress,
            String tokenId,
            String amount) {

        WalletsApi walletsApi = new WalletsApi(client);
        TransactionsApi transactionsApi = new TransactionsApi(client);

        try {
            // Validate destination first
            var validation = walletsApi.checkAddressValidity(tokenId, destinationAddress);
            if (!validation.getIsValid()) {
                throw new RuntimeException("Invalid address: " + validation.getMessage());
            }

            // Create unique request_id
            String requestId = "tx-" + System.currentTimeMillis() + "-" +
                UUID.randomUUID().toString().substring(0, 8);

            // Build source
            WalletTransferSource walletSource = new WalletTransferSource();
            walletSource.setSourceType(TransferSourceType.WALLET);
            walletSource.setWalletId(sourceWalletId);
            TransferSource source = new TransferSource(walletSource);

            // Build destination
            AddressTransferDestination addressDest = new AddressTransferDestination();
            addressDest.setDestinationType(TransferDestinationType.ADDRESS);
            addressDest.setAddress(destinationAddress);
            addressDest.setAmount(amount);
            TransferDestination destination = new TransferDestination(addressDest);

            // Create transfer params
            TransferParams params = new TransferParams();
            params.setRequestId(requestId);
            params.setSource(source);
            params.setTokenId(tokenId);
            params.setDestination(destination);

            TransferResult transaction = transactionsApi.createTransfer(params);

            System.out.println("Created transaction: " + transaction.getTransactionId());
            System.out.println("  Status: " + transaction.getStatus());
            System.out.println("  Request ID: " + transaction.getRequestId());

            return transaction;
        } catch (Exception e) {
            System.err.println("Error creating transfer: " + e.getMessage());
            throw new RuntimeException(e);
        }
    }
}
```

## Check Transaction Status

```java
import com.cobo.waas2.model.TransactionDetail;
import com.cobo.waas2.model.TransactionStatus;
import java.util.Set;

public class TransactionStatusExample {
    public static TransactionDetail getTransactionStatus(ApiClient client, String transactionId) {
        TransactionsApi transactionsApi = new TransactionsApi(client);

        try {
            TransactionDetail tx = transactionsApi.getTransaction(transactionId);

            System.out.println("Transaction " + tx.getTransactionId());
            System.out.println("  Status: " + tx.getStatus());
            System.out.println("  Token: " + tx.getTokenId());
            System.out.println("  Created: " + tx.getCreatedTimestamp());

            return tx;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    // Poll until complete
    public static TransactionDetail waitForCompletion(
            ApiClient client,
            String transactionId,
            long timeoutMs,
            long intervalMs) {

        TransactionsApi transactionsApi = new TransactionsApi(client);

        Set<TransactionStatus> terminalStates = Set.of(
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED,
            TransactionStatus.REJECTED,
            TransactionStatus.CANCELLED
        );

        long deadline = System.currentTimeMillis() + timeoutMs;

        while (System.currentTimeMillis() < deadline) {
            try {
                TransactionDetail tx = transactionsApi.getTransaction(transactionId);
                System.out.println("  Status: " + tx.getStatus());

                if (terminalStates.contains(tx.getStatus())) {
                    return tx;
                }

                Thread.sleep(intervalMs);
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }

        throw new RuntimeException("Transaction " + transactionId +
            " did not complete in " + timeoutMs + "ms");
    }
}
```

## Error Handling

```java
import com.cobo.waas2.ApiException;
import java.util.function.Supplier;

public class ErrorHandlingExample {
    public static <T> T safeApiCall(Supplier<T> operation, int maxRetries) {
        int retryDelay = 1000;

        for (int attempt = 0; attempt < maxRetries; attempt++) {
            try {
                return operation.get();

            } catch (ApiException e) {
                int status = e.getCode();
                System.out.println("API Error " + status + ": " + e.getMessage());

                switch (status) {
                    case 401:
                        throw new RuntimeException("Authentication failed - check COBO_API_SECRET");
                    case 403:
                        throw new RuntimeException("Permission denied - check API key permissions");
                    case 404:
                        throw new RuntimeException("Resource not found: " + e.getResponseBody());
                    case 429:
                        // Rate limited - wait and retry
                        int waitTime = retryDelay * (1 << attempt);
                        System.out.println("Rate limited, waiting " + waitTime + "ms...");
                        try {
                            Thread.sleep(waitTime);
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                        }
                        continue;
                    default:
                        if (status >= 500 && attempt < maxRetries - 1) {
                            try {
                                Thread.sleep(retryDelay);
                            } catch (InterruptedException ie) {
                                Thread.currentThread().interrupt();
                            }
                            continue;
                        }
                }

                throw new RuntimeException(e);
            } catch (Exception e) {
                System.out.println("Unexpected error: " + e.getMessage());
                if (attempt < maxRetries - 1) {
                    try {
                        Thread.sleep(retryDelay);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                    }
                    continue;
                }
                throw new RuntimeException(e);
            }
        }

        throw new RuntimeException("Failed after " + maxRetries + " attempts");
    }

    // Usage
    public static void example(ApiClient client) {
        WalletsApi walletsApi = new WalletsApi(client);

        try {
            WalletInfo wallet = safeApiCall(
                () -> walletsApi.getWalletById("wallet_id"),
                3
            );
            System.out.println("Wallet: " + wallet.getName());
        } catch (RuntimeException e) {
            System.err.println("Error: " + e.getMessage());
        }
    }
}
```

## Complete Example

```java
package com.example.cobowaas;

import com.cobo.waas2.ApiClient;
import com.cobo.waas2.Configuration;
import com.cobo.waas2.Env;
import com.cobo.waas2.api.WalletsApi;
import com.cobo.waas2.api.TransactionsApi;
import com.cobo.waas2.model.*;

public class CoboWaasExample {
    public static void main(String[] args) {
        // Setup
        String apiSecret = System.getenv("COBO_API_SECRET");
        if (apiSecret == null || apiSecret.isEmpty()) {
            System.err.println("Set COBO_API_SECRET environment variable");
            System.exit(1);
        }

        String envStr = System.getenv("COBO_ENV");
        if (envStr == null) envStr = "dev";

        ApiClient client = Configuration.getDefaultApiClient();
        client.setPrivKey(apiSecret);

        Env env = envStr.equalsIgnoreCase("prod") ? Env.PROD : Env.DEV;
        client.setEnv(env);

        WalletsApi walletsApi = new WalletsApi(client);
        TransactionsApi transactionsApi = new TransactionsApi(client);

        try {
            // List existing wallets
            System.out.println("Listing wallets...");
            ListWallets200Response walletResponse = walletsApi.listWallets(
                WalletType.CUSTODIAL, null, null, null, 10, null, null
            );

            for (WalletInfo w : walletResponse.getData()) {
                System.out.printf("  %s: %s%n", w.getName(), w.getWalletId());
            }

            // Create wallet if none exist
            WalletInfo wallet;
            if (walletResponse.getData().isEmpty()) {
                System.out.println("\nCreating wallet...");

                CreateCustodialWalletParams custodialParams = new CreateCustodialWalletParams();
                custodialParams.setName("Test Wallet " + System.currentTimeMillis());
                custodialParams.setWalletType(WalletType.CUSTODIAL);
                custodialParams.setWalletSubtype(WalletSubtype.ASSET);

                CreateWalletParams params = new CreateWalletParams(custodialParams);
                CreatedWalletInfo created = walletsApi.createWallet(params);

                System.out.println("Created: " + created.getWalletId());

                // Convert for subsequent operations
                wallet = new WalletInfo();
                wallet.setWalletId(created.getWalletId());
                wallet.setName(created.getName());
            } else {
                wallet = walletResponse.getData().get(0);
            }

            // Create address
            System.out.printf("%nCreating address for wallet %s...%n", wallet.getWalletId());

            try {
                CreateAddressRequest addressRequest = new CreateAddressRequest();
                addressRequest.setChainId("ETH");

                AddressInfo address = walletsApi.createAddress(
                    wallet.getWalletId(), addressRequest
                );

                System.out.println("Address: " + address.getAddress());
            } catch (Exception e) {
                System.out.println("Address may already exist, listing...");

                var addresses = walletsApi.listAddresses(
                    wallet.getWalletId(), null, null, null, null
                );

                for (var addr : addresses.getData()) {
                    System.out.printf("  %s: %s%n",
                        addr.getChainId(), addr.getAddress());
                }
            }

            System.out.println("\nDone!");

        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}
```

## Environment Setup

```bash
# Set environment variables
export COBO_API_SECRET="<your-64-char-hex-secret>"
export COBO_ENV="dev"

# Run with Maven
mvn exec:java -Dexec.mainClass="com.example.cobowaas.CoboWaasExample"

# Run with Gradle
gradle run
```

## build.gradle Example

```groovy
plugins {
    id 'java'
    id 'application'
}

repositories {
    mavenCentral()
}

dependencies {
    implementation 'com.cobo.waas2:cobo-waas2:1.0.0'
}

application {
    mainClass = 'com.example.cobowaas.CoboWaasExample'
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}
```
