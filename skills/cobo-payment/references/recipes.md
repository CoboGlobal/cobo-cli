# Payment Recipes: End-to-End Workflows

## Permissions Quick Reference

| Recipe | Required Permissions |
|--------|---------------------|
| 1. Create & monitor pay-in order | Payment - Read, Write |
| 2. Process refund | Payment - Read, Write |
| 3. Create payout (crypto) | Payment - Read, Write |
| 4. Create payout (OffRamp/bank) | Payment - Read, Write |
| 5. Query balances | Payment - Read |
| 6. Manage merchants | Payment - Read, Write |
| 7. Counterparty & destination setup | Payment - Read, Write |

Configure permissions: `cobo open developer` → Edit API Key → Permissions → Payment

---

## Recipe 1: Create and Monitor a Pay-in Order

A payer sends crypto to complete a purchase.

```bash
# 1. Check available tokens
cobo get /payments/supported_tokens

# 2. Check exchange rate (optional)
cobo get /payments/exchange_rates/ETH_USDT/USD

# 3. Create pay-in order (note: psp_order_code, not request_id)
cobo post /payments/orders \
  --psp_order_code "order-$(date +%s)-$(openssl rand -hex 4)" \
  --merchant_id M1001 \
  --pricing_currency USD \
  --pricing_amount 100.00 \
  --fee_amount 0.00 \
  --payable_currency ETH_USDT \
  --amount_tolerance 0.5

# 4. Poll order status (repeat until terminal)
cobo get /payments/orders/<order_id>
```

**Response fields:** `order_id` (save), `receive_address` (show to payer), `payable_amount` (crypto amount).

**Terminal statuses:** `Completed`, `Expired`, `Failed`. Poll with `cobo get /payments/orders/<order_id>` every ~15 seconds until one of these is reached.

---

## Recipe 2: Process a Refund

Refund a completed pay-in order to the payer.

```bash
ORDER_ID="<completed_order_id>"
REQUEST_ID="refund-$(date +%s)-$(openssl rand -hex 4)"

# 1. Get order details to confirm it's completed and get token/amount
cobo get /payments/orders/$ORDER_ID

# 2. Create refund (payer address known upfront)
cobo post /payments/refunds \
  --request_id "$REQUEST_ID" \
  --order_id "$ORDER_ID" \
  --amount 99.5 \
  --to_address "0x..."

# 3. If to_address not known, omit it — payer submits via refund link
# Refund status will be AddressPending → AddressSubmitted → Pending → Processing → Completed

REFUND_ID="<refund_id_from_response>"

# 4. Monitor refund status
cobo get /payments/refunds/$REFUND_ID
```

---

## Recipe 3: Create a Crypto Payout

Send accumulated merchant funds to a crypto address.

```bash
REQUEST_ID="payout-$(date +%s)-$(openssl rand -hex 4)"

# 1. Check merchant balance first
cobo get /payments/balance/merchants

# 2. Create crypto payout from merchant account
cobo post /payments/payouts \
  --request_id "$REQUEST_ID" \
  --payout_channel Crypto \
  --source_account M1001 \
  --payout_items '[{"token_id":"USDT_ETH","amount":"500","to_address":"0x..."}]'

PAYOUT_ID="<payout_id_from_response>"

# 3. Monitor payout status
cobo get /payments/payouts/$PAYOUT_ID
```

**Terminal statuses:** `Completed`, `PartiallyCompleted`, `Failed`, `RejectedByBank`

---

## Recipe 4: Create an OffRamp Payout (Bank Transfer)

Settle crypto balance to a fiat bank account.

```bash
# 1. Check counterparty bank accounts
cobo get /payments/counterparty
cobo get /payments/counterparty_entry

# 2. Check PSP balance
cobo get /payments/balance/psp

# 3. Create OffRamp payout
REQUEST_ID="payout-$(date +%s)-$(openssl rand -hex 4)"

cobo post /payments/payouts \
  --request_id "$REQUEST_ID" \
  --payout_channel OffRamp \
  --source_account developer \
  --payout_items '[{"amount":"1000","currency":"USD","counterparty_entry_id":"<entry_id>"}]'

# 4. Monitor
PAYOUT_ID="<payout_id_from_response>"
cobo get /payments/payouts/$PAYOUT_ID
```

---

## Recipe 5: Query Balances

```bash
# Merchant balances (all merchants)
cobo get /payments/balance/merchants

# Specific merchant
cobo get /payments/balance/merchants --merchant_id M1001

# PSP (developer) account balance
cobo get /payments/balance/psp

# Payment wallet balances
cobo get /payments/balance/payment_wallets
```

---

## Recipe 6: Manage Merchants

```bash
# List all merchants
cobo get /payments/merchants

# Create merchant with dedicated wallet
cobo post /payments/merchants \
  --name "Acme Store" \
  --wallet_setup Separate

# Create merchant with shared wallet (cost-efficient)
cobo post /payments/merchants \
  --name "Small Shop" \
  --wallet_setup Shared

# Get specific merchant by ID
cobo get /payments/merchants/<merchant_id>

# Search merchant by name
cobo get /payments/merchants --keyword "Acme"
```

---

## Recipe 7: Create a Counterparty (Python SDK)

> **CLI limitation:** `wallet_addresses` is a required JSON array — use Python SDK instead of CLI.

```bash
eval $(cobo config env)
```

```python
import cobo_waas2, os
from cobo_waas2.models import CreateCounterpartyRequest, CreateWalletAddress

configuration = cobo_waas2.Configuration(
    api_private_key=os.environ["COBO_API_SECRET"],
    host="https://api.dev.cobo.com/v2"   # change to api.cobo.com for prod
)

with cobo_waas2.ApiClient(configuration) as api_client:
    api = cobo_waas2.PaymentApi(api_client)
    resp = api.create_counterparty(
        create_counterparty_request=CreateCounterpartyRequest(
            counterparty_name="Acme Corp",
            counterparty_type="Organization",  # Individual or Organization
            wallet_addresses=[
                CreateWalletAddress(address="0x...", chain_id="ETH")
            ],
            country="USA",    # optional, ISO 3166-1 alpha-3
            email="acme@example.com"  # optional
        )
    )
    print(resp.counterparty_id)
```

```bash
# Add more wallet addresses later via counterparty_entry
cobo get /payments/counterparty_entry --counterparty_id <counterparty_id>
```

> **Note:** `counterparty_entry` supports wallet addresses only — bank accounts are **not** creatable via API.

---

## Recipe 8: Create a Payment Link

> **CLI cannot be used for this endpoint** — `business_info` is a complex nested object that the CLI mishandles (error 2006). Use the Python SDK instead.

Payment links create a **new order internally** — do not pass an existing `order_id`.

```bash
# Load env vars from cobo config
eval $(cobo config env)
```

```python
import time, secrets, cobo_waas2, os
from cobo_waas2.models import CreateOrderLinkRequest, OrderLinkBusinessInfo

configuration = cobo_waas2.Configuration(
    api_private_key=os.environ["COBO_API_SECRET"],
    host="https://api.dev.cobo.com/v2"   # change to api.cobo.com for prod
)

with cobo_waas2.ApiClient(configuration) as api_client:
    api = cobo_waas2.PaymentApi(api_client)
    business_info = OrderLinkBusinessInfo(
        merchant_id="M1017",
        psp_order_code=f"P-{int(time.time())}-{secrets.token_hex(4)}",
        pricing_currency="USD",
        pricing_amount="1000.00",
        fee_amount="200.00",
        payable_currencies=["TRON_USDT"]   # array, not a string
    )
    resp = api.create_order_link(
        create_order_link_request=CreateOrderLinkRequest(business_info=business_info)
    )
    print(f"{resp.url}?token={resp.token}")
```

**Response:** `url` + `token` — combine as `{url}?token={token}` to get the shareable link.

---

## Recipe 9: Create a Destination (Python SDK for bank accounts)

> For wallet-only destinations, CLI works: `cobo post /payments/destination --destination_name "X" --destination_type Individual --wallet_addresses '[{"address":"0x...","chain_id":"ETH"}]'`
>
> For bank accounts, use Python SDK — the nested structure is too complex for CLI.

```bash
eval $(cobo config env)
```

```python
import cobo_waas2, os
from cobo_waas2.models import CreateDestinationRequest, CreateDestinationBankAccount

configuration = cobo_waas2.Configuration(
    api_private_key=os.environ["COBO_API_SECRET"],
    host="https://api.dev.cobo.com/v2"   # change to api.cobo.com for prod
)

with cobo_waas2.ApiClient(configuration) as api_client:
    api = cobo_waas2.PaymentApi(api_client)
    resp = api.create_destination(
        create_destination_request=CreateDestinationRequest(
            destination_name="Acme Dest",
            destination_type="Organization",  # Individual or Organization
            merchant_id="M1001",   # optional: link to specific merchant
            bank_accounts=[
                CreateDestinationBankAccount(
                    account_alias="main",
                    account_number="...",
                    swift_code="...",
                    currency="USD",
                    beneficiary_name="Acme Corp",
                    beneficiary_address="123 Main St, New York, USA",
                    bank_name="...",
                    bank_address="..."
                )
            ]
        )
    )
    print(resp.destination_id)
```

---

## Quick Reference

| Task | Recipe |
|------|--------|
| Accept crypto payment | Recipe 1 |
| Refund a payment | Recipe 2 |
| Pay out to crypto address | Recipe 3 |
| Pay out to bank account | Recipe 4 |
| Check balances | Recipe 5 |
| Create/manage merchant | Recipe 6 |
| Create counterparty | Recipe 7 |
| Create payment link | Recipe 8 |
| Create destination with bank account | Recipe 9 |
