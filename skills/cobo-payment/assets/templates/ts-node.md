# Payment SDK — TypeScript / Node.js

## Setup

```typescript
import CoboWaas2 from "@cobo/cobo-waas2";

const client = CoboWaas2.createConfiguration({
  apiSecret: process.env.COBO_API_SECRET!,
  env: process.env.COBO_ENV || "dev",
});
const paymentApi = new CoboWaas2.PaymentApi(client);
```

## List Orders

```typescript
const response = await paymentApi.listOrders({ limit: 10 });
response.data.forEach(order => {
  console.log(`${order.order_id}: ${order.status}`);
});
```

## Create Pay-in Order

```typescript
import crypto from "crypto";

const response = await paymentApi.createOrder({
  request_id: `order-${Date.now()}-${crypto.randomBytes(4).toString("hex")}`,
  merchant_id: "M1001",
  pricing_currency: "USD",
  pricing_amount: "100.00",
  payable_currency: "USDT_ETH",
  amount_tolerance: "0.5",
});
console.log(`Order: ${response.order_id}, Pay to: ${response.receive_address}`);
```

## Create Payout

```typescript
const response = await paymentApi.createPayout({
  request_id: `payout-${Date.now()}-${crypto.randomBytes(4).toString("hex")}`,
  payout_channel: "Crypto",
  source_account: "M1001",
  payout_items: [{ token_id: "USDT_ETH", amount: "500", to_address: "0x..." }],
});
console.log(`Payout: ${response.payout_id}`);
```
