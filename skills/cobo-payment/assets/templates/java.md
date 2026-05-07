# Payment SDK — Java

## Setup

```java
import com.cobo.waas2.ApiClient;
import com.cobo.waas2.api.PaymentApi;
import com.cobo.waas2.model.*;

ApiClient client = new ApiClient();
client.setEnv(System.getenv("COBO_ENV") != null ? System.getenv("COBO_ENV") : "dev");
client.setPrivKey(System.getenv("COBO_API_SECRET"));
PaymentApi paymentApi = new PaymentApi(client);
```

## List Orders

```java
ListOrdersResponse resp = paymentApi.listOrders(10, null, null, null, null, null);
for (Order order : resp.getData()) {
    System.out.printf("%s: %s%n", order.getOrderId(), order.getStatus());
}
```

## Create Pay-in Order

```java
import java.util.UUID;

CreateOrderRequest req = new CreateOrderRequest()
    .requestId("order-" + System.currentTimeMillis() + "-" + UUID.randomUUID().toString().substring(0, 8))
    .merchantId("M1001")
    .pricingCurrency("USD")
    .pricingAmount("100.00")
    .payableCurrency("USDT_ETH")
    .amountTolerance("0.5");

Order order = paymentApi.createOrder(req);
System.out.printf("Order: %s, Pay to: %s%n", order.getOrderId(), order.getReceiveAddress());
```
