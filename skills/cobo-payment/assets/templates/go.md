# Payment SDK — Go

## Setup

```go
import (
    cobo "github.com/CoboGlobal/cobo-waas2-go-sdk/cobo_waas2"
    "os"
)

cfg := cobo.NewConfiguration()
cfg.SetEnv(os.Getenv("COBO_ENV"))
cfg.SetApiSecret(os.Getenv("COBO_API_SECRET"))
client := cobo.NewAPIClient(cfg)
```

## List Orders

```go
resp, _, err := client.PaymentAPI.ListOrders(ctx).Limit(10).Execute()
if err != nil { log.Fatal(err) }
for _, order := range resp.Data {
    fmt.Printf("%s: %s\n", order.OrderId, order.Status)
}
```

## Create Pay-in Order

```go
import (
    "fmt"
    "time"
    "encoding/hex"
    "crypto/rand"
)

b := make([]byte, 4)
rand.Read(b)
requestId := fmt.Sprintf("order-%d-%s", time.Now().Unix(), hex.EncodeToString(b))

resp, _, err := client.PaymentAPI.CreateOrder(ctx).CreateOrderRequest(
    cobo.CreateOrderRequest{
        RequestId:       requestId,
        MerchantId:      "M1001",
        PricingCurrency: "USD",
        PricingAmount:   "100.00",
        PayableCurrency: cobo.PtrString("USDT_ETH"),
        AmountTolerance: cobo.PtrString("0.5"),
    },
).Execute()
if err != nil { log.Fatal(err) }
fmt.Printf("Order: %s, Pay to: %s\n", resp.OrderId, *resp.ReceiveAddress)
```
