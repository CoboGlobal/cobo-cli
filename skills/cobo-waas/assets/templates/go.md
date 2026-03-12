# Go SDK Sample (WaaS 2.0)

Complete Go SDK examples for Cobo WaaS 2.0 operations.

## Installation

```bash
go get github.com/CoboGlobal/cobo-waas2-go-sdk
```

## go.mod

```go
module example.com/cobo-waas-example

go 1.22

require github.com/CoboGlobal/cobo-waas2-go-sdk v1.0.0
```

## Environment (all languages)

- **macOS / Linux:** `eval $(cobo config env)`
- **Windows PowerShell:** `cobo config env --format powershell | Invoke-Expression`
- **Windows CMD:** `cobo config env --format cmd > env.bat && env.bat`

## Configuration from Environment

```go
package main

import (
    "context"
    "fmt"
    "os"

    cobo_waas2 "github.com/CoboGlobal/cobo-waas2-go-sdk/cobo_waas2"
    "github.com/CoboGlobal/cobo-waas2-go-sdk/cobo_waas2/crypto"
)

func getContext() context.Context {
    // Read from environment variables (recommended)
    apiSecret := os.Getenv("COBO_API_SECRET")
    if apiSecret == "" {
        panic("COBO_API_SECRET environment variable not set")
    }

    env := os.Getenv("COBO_ENV")
    if env == "" {
        env = "dev"
    }

    // Set environment
    var coboEnv cobo_waas2.Env
    switch env {
    case "prod":
        coboEnv = cobo_waas2.ProdEnv
    case "sandbox":
        coboEnv = cobo_waas2.SandboxEnv
    default:
        coboEnv = cobo_waas2.DevEnv
    }

    ctx := context.Background()
    ctx = context.WithValue(ctx, cobo_waas2.ContextEnv, coboEnv)
    ctx = context.WithValue(ctx, cobo_waas2.ContextPortalSigner, crypto.Ed25519Signer(apiSecret))

    return ctx
}

func getClient() *cobo_waas2.APIClient {
    cfg := cobo_waas2.NewConfiguration()
    return cobo_waas2.NewAPIClient(cfg)
}
```

## List Wallets

```go
func listWallets(ctx context.Context, client *cobo_waas2.APIClient) {
    // List all wallets
    resp, httpResp, err := client.WalletsAPI.ListWallets(ctx).
        Limit(10).
        Execute()

    if err != nil {
        fmt.Printf("Error: %v\n", err)
        fmt.Printf("HTTP Response: %v\n", httpResp)
        return
    }

    fmt.Printf("Found %d wallets\n", len(resp.Data))
    for _, wallet := range resp.Data {
        fmt.Printf("  %s: %s (%s)\n",
            wallet.GetWalletId(),
            wallet.GetName(),
            wallet.GetWalletType())
    }
}

// Filter by wallet type
func listCustodialWallets(ctx context.Context, client *cobo_waas2.APIClient) {
    walletType := cobo_waas2.WALLETTYPE_CUSTODIAL

    resp, _, err := client.WalletsAPI.ListWallets(ctx).
        WalletType(walletType).
        Limit(50).
        Execute()

    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    for _, wallet := range resp.Data {
        fmt.Printf("%s: %s\n", wallet.GetWalletId(), wallet.GetName())
    }
}

// Pagination
func listAllWallets(ctx context.Context, client *cobo_waas2.APIClient) []cobo_waas2.WalletInfo {
    var allWallets []cobo_waas2.WalletInfo
    var after string

    for {
        req := client.WalletsAPI.ListWallets(ctx).Limit(100)
        if after != "" {
            req = req.After(after)
        }

        resp, _, err := req.Execute()
        if err != nil {
            break
        }

        allWallets = append(allWallets, resp.Data...)

        if resp.Pagination == nil || resp.Pagination.After == nil {
            break
        }
        after = *resp.Pagination.After
    }

    return allWallets
}
```

## Create Custodial Wallet

```go
func createCustodialWallet(ctx context.Context, client *cobo_waas2.APIClient, name string) (*cobo_waas2.CreatedWalletInfo, error) {
    walletType := cobo_waas2.WALLETTYPE_CUSTODIAL
    walletSubtype := cobo_waas2.WALLETSUBTYPE_ASSET

    params := cobo_waas2.CreateWalletParams{
        CreateCustodialWalletParams: &cobo_waas2.CreateCustodialWalletParams{
            Name:          name,
            WalletType:    walletType,
            WalletSubtype: walletSubtype,
        },
    }

    wallet, httpResp, err := client.WalletsAPI.CreateWallet(ctx).
        CreateWalletParams(params).
        Execute()

    if err != nil {
        fmt.Printf("Error: %v\n", err)
        fmt.Printf("HTTP Response: %v\n", httpResp)
        return nil, err
    }

    fmt.Printf("Created wallet: %s\n", wallet.GetWalletId())
    fmt.Printf("  Name: %s\n", wallet.GetName())
    fmt.Printf("  Type: %s/%s\n", wallet.GetWalletType(), wallet.GetWalletSubtype())

    return wallet, nil
}
```

## Create MPC Org-Controlled Wallet

```go
func createMpcWallet(ctx context.Context, client *cobo_waas2.APIClient, name string, vaultId string) (*cobo_waas2.CreatedWalletInfo, error) {
    walletType := cobo_waas2.WALLETTYPE_MPC
    walletSubtype := cobo_waas2.WALLETSUBTYPE_ORG_CONTROLLED

    params := cobo_waas2.CreateWalletParams{
        CreateMpcWalletParams: &cobo_waas2.CreateMpcWalletParams{
            Name:          name,
            WalletType:    walletType,
            WalletSubtype: walletSubtype,
            VaultId:       vaultId,
        },
    }

    wallet, _, err := client.WalletsAPI.CreateWallet(ctx).
        CreateWalletParams(params).
        Execute()

    if err != nil {
        return nil, err
    }

    fmt.Printf("Created MPC wallet: %s\n", wallet.GetWalletId())
    return wallet, nil
}

// Get vault_id first
func getVaultId(ctx context.Context, client *cobo_waas2.APIClient) (string, error) {
    resp, _, err := client.WalletsAPI.ListMpcVaults(ctx).Execute()
    if err != nil {
        return "", err
    }

    if len(resp.Data) == 0 {
        return "", fmt.Errorf("no vaults found")
    }

    return resp.Data[0].GetVaultId(), nil
}
```

## Create Address

```go
func createAddress(ctx context.Context, client *cobo_waas2.APIClient, walletId string, chainId string) (*cobo_waas2.AddressInfo, error) {
    // Get supported chains first
    chains, _, err := client.WalletsAPI.ListSupportedChains(ctx, walletId).Execute()
    if err != nil {
        return nil, err
    }

    fmt.Printf("Supported chains: ")
    for _, chain := range chains.Data {
        fmt.Printf("%s ", chain.GetChainId())
    }
    fmt.Println()

    // Create address
    params := cobo_waas2.CreateAddressRequest{
        ChainId: chainId,
    }

    address, _, err := client.WalletsAPI.CreateAddress(ctx, walletId).
        CreateAddressRequest(params).
        Execute()

    if err != nil {
        return nil, err
    }

    fmt.Printf("Created address: %s\n", address.GetAddress())
    fmt.Printf("  Chain: %s\n", address.GetChainId())
    fmt.Printf("  Address ID: %s\n", address.GetAddressId())

    return address, nil
}
```

## Create Transfer

```go
import (
    "fmt"
    "time"
    "crypto/rand"
    "encoding/hex"
)

func generateRequestId() string {
    b := make([]byte, 4)
    rand.Read(b)
    return fmt.Sprintf("tx-%d-%s", time.Now().Unix(), hex.EncodeToString(b))
}

func createTransfer(
    ctx context.Context,
    client *cobo_waas2.APIClient,
    sourceWalletId string,
    destinationAddress string,
    tokenId string,
    amount string,
) (*cobo_waas2.TransferResult, error) {
    // Validate destination first
    validation, _, err := client.WalletsAPI.CheckAddressValidity(ctx).
        ChainId(tokenId).
        Address(destinationAddress).
        Execute()

    if err != nil {
        return nil, err
    }

    if !validation.GetIsValid() {
        return nil, fmt.Errorf("invalid address: %s", validation.GetMessage())
    }

    // Create unique request_id
    requestId := generateRequestId()

    // Build transfer params
    source := cobo_waas2.TransferSource{
        WalletTransferSource: &cobo_waas2.WalletTransferSource{
            SourceType: cobo_waas2.TRANSFERSOURCETYPE_WALLET,
            WalletId:   sourceWalletId,
        },
    }

    destination := cobo_waas2.TransferDestination{
        AddressTransferDestination: &cobo_waas2.AddressTransferDestination{
            DestinationType: cobo_waas2.TRANSFERDESTINATIONTYPE_ADDRESS,
            Address:         destinationAddress,
            Amount:          amount,
        },
    }

    params := cobo_waas2.TransferParams{
        RequestId:   requestId,
        Source:      source,
        TokenId:     tokenId,
        Destination: destination,
    }

    transaction, _, err := client.TransactionsAPI.CreateTransfer(ctx).
        TransferParams(params).
        Execute()

    if err != nil {
        return nil, err
    }

    fmt.Printf("Created transaction: %s\n", transaction.GetTransactionId())
    fmt.Printf("  Status: %s\n", transaction.GetStatus())
    fmt.Printf("  Request ID: %s\n", transaction.GetRequestId())

    return transaction, nil
}
```

## Check Transaction Status

```go
func getTransactionStatus(ctx context.Context, client *cobo_waas2.APIClient, transactionId string) (*cobo_waas2.TransactionDetail, error) {
    tx, _, err := client.TransactionsAPI.GetTransaction(ctx, transactionId).Execute()
    if err != nil {
        return nil, err
    }

    fmt.Printf("Transaction %s\n", tx.GetTransactionId())
    fmt.Printf("  Status: %s\n", tx.GetStatus())
    fmt.Printf("  Token: %s\n", tx.GetTokenId())
    fmt.Printf("  Created: %d\n", tx.GetCreatedTimestamp())

    return tx, nil
}

// Poll until complete
func waitForCompletion(
    ctx context.Context,
    client *cobo_waas2.APIClient,
    transactionId string,
    timeout time.Duration,
    interval time.Duration,
) (*cobo_waas2.TransactionDetail, error) {
    terminalStates := map[cobo_waas2.TransactionStatus]bool{
        cobo_waas2.TRANSACTIONSTATUS_COMPLETED: true,
        cobo_waas2.TRANSACTIONSTATUS_FAILED:    true,
        cobo_waas2.TRANSACTIONSTATUS_REJECTED:  true,
        cobo_waas2.TRANSACTIONSTATUS_CANCELLED: true,
    }

    deadline := time.Now().Add(timeout)

    for time.Now().Before(deadline) {
        tx, _, err := client.TransactionsAPI.GetTransaction(ctx, transactionId).Execute()
        if err != nil {
            return nil, err
        }

        fmt.Printf("  Status: %s\n", tx.GetStatus())

        if terminalStates[tx.GetStatus()] {
            return tx, nil
        }

        time.Sleep(interval)
    }

    return nil, fmt.Errorf("transaction %s did not complete in %v", transactionId, timeout)
}
```

## Error Handling

```go
import (
    "net/http"
    "time"
)

func safeApiCall[T any](
    operation func() (T, *http.Response, error),
    maxRetries int,
) (T, error) {
    var zero T
    retryDelay := time.Second

    for attempt := 0; attempt < maxRetries; attempt++ {
        result, httpResp, err := operation()

        if err == nil {
            return result, nil
        }

        // Extract status code
        statusCode := 0
        if httpResp != nil {
            statusCode = httpResp.StatusCode
        }

        fmt.Printf("API Error %d: %v\n", statusCode, err)

        switch statusCode {
        case 401:
            return zero, fmt.Errorf("authentication failed - check COBO_API_SECRET")
        case 403:
            return zero, fmt.Errorf("permission denied - check API key permissions")
        case 404:
            return zero, fmt.Errorf("resource not found")
        case 429:
            // Rate limited - wait and retry
            waitTime := retryDelay * time.Duration(1<<attempt)
            fmt.Printf("Rate limited, waiting %v...\n", waitTime)
            time.Sleep(waitTime)
            continue
        default:
            if statusCode >= 500 && attempt < maxRetries-1 {
                time.Sleep(retryDelay)
                continue
            }
        }

        return zero, err
    }

    return zero, fmt.Errorf("failed after %d attempts", maxRetries)
}

// Usage
func example(ctx context.Context, client *cobo_waas2.APIClient) {
    wallet, err := safeApiCall(func() (*cobo_waas2.WalletInfo, *http.Response, error) {
        return client.WalletsAPI.GetWalletById(ctx, "wallet_id").Execute()
    }, 3)

    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    fmt.Printf("Wallet: %s\n", wallet.GetName())
}
```

## Complete Example

```go
package main

import (
    "context"
    "fmt"
    "os"
    "time"

    cobo_waas2 "github.com/CoboGlobal/cobo-waas2-go-sdk/cobo_waas2"
    "github.com/CoboGlobal/cobo-waas2-go-sdk/cobo_waas2/crypto"
)

func main() {
    // Setup
    apiSecret := os.Getenv("COBO_API_SECRET")
    if apiSecret == "" {
        fmt.Println("Set COBO_API_SECRET environment variable")
        os.Exit(1)
    }

    env := os.Getenv("COBO_ENV")
    if env == "" {
        env = "dev"
    }

    var coboEnv cobo_waas2.Env
    switch env {
    case "prod":
        coboEnv = cobo_waas2.ProdEnv
    default:
        coboEnv = cobo_waas2.DevEnv
    }

    ctx := context.Background()
    ctx = context.WithValue(ctx, cobo_waas2.ContextEnv, coboEnv)
    ctx = context.WithValue(ctx, cobo_waas2.ContextPortalSigner, crypto.Ed25519Signer(apiSecret))

    cfg := cobo_waas2.NewConfiguration()
    client := cobo_waas2.NewAPIClient(cfg)

    // List existing wallets
    fmt.Println("Listing wallets...")
    walletType := cobo_waas2.WALLETTYPE_CUSTODIAL

    resp, _, err := client.WalletsAPI.ListWallets(ctx).
        WalletType(walletType).
        Limit(10).
        Execute()

    if err != nil {
        fmt.Printf("Error: %v\n", err)
        os.Exit(1)
    }

    for _, w := range resp.Data {
        fmt.Printf("  %s: %s\n", w.GetName(), w.GetWalletId())
    }

    // Create wallet if none exist
    var wallet *cobo_waas2.WalletInfo
    if len(resp.Data) == 0 {
        fmt.Println("\nCreating wallet...")

        params := cobo_waas2.CreateWalletParams{
            CreateCustodialWalletParams: &cobo_waas2.CreateCustodialWalletParams{
                Name:          fmt.Sprintf("Test Wallet %d", time.Now().Unix()),
                WalletType:    cobo_waas2.WALLETTYPE_CUSTODIAL,
                WalletSubtype: cobo_waas2.WALLETSUBTYPE_ASSET,
            },
        }

        created, _, err := client.WalletsAPI.CreateWallet(ctx).
            CreateWalletParams(params).
            Execute()

        if err != nil {
            fmt.Printf("Error creating wallet: %v\n", err)
            os.Exit(1)
        }

        fmt.Printf("Created: %s\n", created.GetWalletId())
        // Convert CreatedWalletInfo to WalletInfo for subsequent operations
        wallet = &cobo_waas2.WalletInfo{
            WalletId: created.WalletId,
            Name:     created.Name,
        }
    } else {
        wallet = &resp.Data[0]
    }

    // Create address
    fmt.Printf("\nCreating address for wallet %s...\n", wallet.GetWalletId())

    addressParams := cobo_waas2.CreateAddressRequest{
        ChainId: "ETH",
    }

    address, _, err := client.WalletsAPI.CreateAddress(ctx, wallet.GetWalletId()).
        CreateAddressRequest(addressParams).
        Execute()

    if err != nil {
        fmt.Println("Address may already exist, listing...")

        addresses, _, _ := client.WalletsAPI.ListAddresses(ctx, wallet.GetWalletId()).Execute()
        for _, addr := range addresses.Data {
            fmt.Printf("  %s: %s\n", addr.GetChainId(), addr.GetAddress())
        }
    } else {
        fmt.Printf("Address: %s\n", address.GetAddress())
    }

    fmt.Println("\nDone!")
}
```

## Environment Setup

```bash
# Set environment variables
export COBO_API_SECRET="<your-64-char-hex-secret>"
export COBO_ENV="dev"

# Run
go run main.go
```
