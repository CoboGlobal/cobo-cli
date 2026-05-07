# Payment SDK — Python

## Setup

```python
import os
from cobo_waas2 import Configuration, ApiClient
from cobo_waas2.api import PaymentApi

config = Configuration(
    api_private_key=os.environ["COBO_API_SECRET"],
    host="https://api.{}.cobo.com/v2".format(os.environ.get("COBO_ENV", "dev")).replace("prod.", "")
    if os.environ.get("COBO_ENV", "dev") != "prod"
    else "https://api.cobo.com/v2",
)
client = ApiClient(config)
payment_api = PaymentApi(client)
```

## List Orders

```python
response = payment_api.list_orders(limit=10)
for order in response.data:
    print(f"{order.order_id}: {order.status} - {order.pricing_amount} {order.pricing_currency}")
```

## Create Pay-in Order

```python
import time, os
from cobo_waas2.models import CreateOrderRequest

response = payment_api.create_order(create_order_request=CreateOrderRequest(
    request_id=f"order-{int(time.time())}-{os.urandom(4).hex()}",
    merchant_id="M1001",
    pricing_currency="USD",
    pricing_amount="100.00",
    payable_currency="USDT_ETH",
    amount_tolerance="0.5",
))
print(f"Order: {response.order_id}, Pay to: {response.receive_address}")
```

## Create Refund

```python
from cobo_waas2.models import CreateRefundRequest

response = payment_api.create_refund(create_refund_request=CreateRefundRequest(
    request_id=f"refund-{int(time.time())}-{os.urandom(4).hex()}",
    order_id="<order_id>",
    amount="99.50",
    to_address="0x...",
))
print(f"Refund: {response.refund_id}, Status: {response.status}")
```

## Create Payout

```python
from cobo_waas2.models import CreatePayoutRequest

response = payment_api.create_payout(create_payout_request=CreatePayoutRequest(
    request_id=f"payout-{int(time.time())}-{os.urandom(4).hex()}",
    payout_channel="Crypto",
    source_account="M1001",
    payout_items=[{"token_id": "USDT_ETH", "amount": "500", "to_address": "0x..."}],
))
print(f"Payout: {response.payout_id}, Status: {response.status}")
```

## Check Merchant Balance

```python
response = payment_api.get_merchant_balance(merchant_id="M1001")
for balance in response.data:
    print(f"{balance.token_id}: {balance.balance}")
```

## Error Handling

```python
from cobo_waas2.exceptions import ApiException
import json

try:
    response = payment_api.create_order(...)
except ApiException as e:
    print(f"HTTP {e.status}: {e.reason}")
    body = json.loads(e.body)
    if body.get("error_code") == 30001:
        print("Duplicate request_id — generate a new one")
    elif e.status == 403:
        print("Missing Payment permission — check API key in Portal")
```

## Polling Pattern

```python
import time

def wait_for_order(order_id, timeout=600, interval=15):
    terminal = {"Completed", "Expired", "Failed"}
    start = time.time()
    while time.time() - start < timeout:
        order = payment_api.get_order(order_id=order_id)
        print(f"Status: {order.status}")
        if order.status in terminal:
            return order
        time.sleep(interval)
    raise TimeoutError(f"Order {order_id} did not reach terminal state")
```
