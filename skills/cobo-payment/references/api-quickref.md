# Payment API Quick Reference

All endpoints are under `/payments/*`. Use `cobo doc /payments/<path>` to get full parameter details before generating requests.

## Endpoint Discovery

```bash
cobo get --list | grep payments   # List all payment GET endpoints
cobo post --list | grep payments  # List all payment POST endpoints
cobo doc /payments/orders         # Full parameter docs for an endpoint
```

---

## Merchants

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/merchants` | List all merchants (filter: keyword, wallet_setup) |
| POST | `/payments/merchants` | Create a merchant |
| GET | `/payments/merchants/{merchant_id}` | Get merchant details |

Key parameters for `POST /payments/merchants`:
- `name` (required) — Merchant name
- `wallet_setup` — `Shared` / `Separate` (default: `Shared`)

---

## Pay-in Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/orders` | List orders (filter: merchant_id, psp_order_id, statuses) |
| POST | `/payments/orders` | Create a pay-in order |
| GET | `/payments/orders/{order_id}` | Get order details |

Key parameters for `POST /payments/orders`:
- `psp_order_code` (required) — Your unique idempotency key (assigned by you as developer)
- `merchant_id` (required) — Target merchant
- `pricing_currency` — Fiat currency (e.g. `USD`); if omitted, denominated in `payable_currency`
- `pricing_amount` — Base fiat amount, 2 decimal places (e.g. `"100.00"`)
- `fee_amount` (required) — Developer fee, 2 decimal places (use `"0.00"` if none)
- `payable_currency` (required) — Crypto token (e.g. `TRON_USDT`, `ETH_USDT`)
- `payable_amount` — Crypto amount; if omitted, calculated from exchange rate
- `amount_tolerance` — Allowed underpayment (e.g. `0.5`)
- `expired_in` — Seconds until expiry (default 1800, max 10800)
- `merchant_order_code` — Merchant's own reference code

---

## Refunds

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/refunds` | List refunds (filter: merchant_id, request_id, statuses) |
| POST | `/payments/refunds` | Create a refund |
| GET | `/payments/refunds/{refund_id}` | Get refund details |

Key parameters for `POST /payments/refunds`:
- `request_id` (required) — Unique idempotency key
- `order_id` (required) — The pay-in order to refund
- `amount` (required) — Crypto amount to refund
- `to_address` — Refund destination address (if known upfront)

---

## Payouts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/payouts` | List payouts (filter: request_id) |
| POST | `/payments/payouts` | Create a payout |
| GET | `/payments/payouts/{payout_id}` | Get payout details |

Key parameters for `POST /payments/payouts`:
- `request_id` (required) — Unique idempotency key
- `payout_channel` (required) — `Crypto` or `OffRamp`
- `source_account` (required) — Merchant ID or `"developer"`
- `payout_items` (required) — Array of payout line items

> **Note**: `/payments/settlement_requests` is deprecated. Use `/payments/payouts` instead.

---

## Bulk Sends

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/bulk_sends/{bulk_send_id}` | Get bulk send details |
| GET | `/payments/bulk_sends/{bulk_send_id}/items` | List items in a bulk send |

---

## Balances

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/balance/payment_wallets` | Balances by payment wallet |
| GET | `/payments/balance/merchants` | Balances by merchant |
| GET | `/payments/balance/psp` | PSP (developer) account balance |

---

## Crypto Addresses & Top-up

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/crypto_addresses` | List crypto addresses |
| GET | `/payments/topup/address` | Get top-up address |
| GET | `/payments/topup/payers` | List top-up payers |
| GET | `/payments/topup/payer_accounts` | List top-up payer accounts |
| POST | `/payments/force_sweep_requests` | Force a sweep of funds |

---

## Counterparties

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/counterparty` | List counterparties |
| POST | `/payments/counterparty` | Create a counterparty |
| GET | `/payments/counterparty/{counterparty_id}` | Get counterparty |
| PUT | `/payments/counterparty/{counterparty_id}` | Update counterparty |
| GET | `/payments/counterparty_entry` | List counterparty entries |
| POST | `/payments/counterparty_entry` | Create a counterparty entry |
| GET | `/payments/counterparty_entry/{counterparty_entry_id}` | Get counterparty entry |

Key parameters for `POST /payments/counterparty`:
- `counterparty_name` (required) — Counterparty name
- `counterparty_type` (required) — `Individual` or `Organization`
- `wallet_addresses` (required) — JSON array: `[{"address":"0x...","chain_id":"ETH"}]`
- `country` — ISO 3166-1 alpha-3 (e.g. `USA`)
- `email` — Contact email

> **CLI limitation:** `wallet_addresses` is a required JSON array — use Python SDK instead (see `recipes.md` Recipe 7).
> **Note:** `counterparty_entry` supports wallet addresses only — bank accounts are **not** creatable via API.

---

## Destinations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/destination` | List destinations |
| POST | `/payments/destination` | Create a destination |
| GET | `/payments/destination/{destination_id}` | Get destination |
| GET | `/payments/destination_entry` | List destination entries |
| POST | `/payments/destination_entry` | Create a destination entry |
| GET | `/payments/destination_entry/{destination_entry_id}` | Get destination entry |

Key parameters for `POST /payments/destination`:
- `destination_name` (required) — Destination name
- `destination_type` (required) — `Individual` or `Organization`
- `wallet_addresses` — JSON array (simple, CLI works): `[{"address":"0x...","chain_id":"ETH"}]`
- `bank_accounts` — JSON array with nested fields (complex — use Python SDK, see `recipes.md` Recipe 9)
- `merchant_id` — Link to specific merchant

---

## Allocations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/allocation_amount` | Get allocation amounts |
| GET | `/payments/batch_allocations` | List batch allocations |
| POST | `/payments/batch_allocations` | Create batch allocation |
| GET | `/payments/batch_allocations/{batch_allocation_id}` | Get batch allocation |
| GET | `/payments/allocation_items` | List allocation items |

---

## Reports & Settlement

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/reports` | List settlement reports |
| POST | `/payments/reports` | Generate a report |
| GET | `/payments/settlement_info` | Get settlement configuration |
| GET | `/payments/settlement_details` | Get settlement transaction details |
| GET | `/payments/bank_accounts` | List registered bank accounts |

> **Known issue:** `POST /payments/reports` accepts `report_export_format: ZIP` as a parameter (present in the SDK), but this does **not** work — do not use `ZIP`. Use `CSV` or `XLSX` instead.

---

## Payment Links

> **Important:** `POST /payments/links/orders` and `POST /payments/links/refunds` accept complex nested JSON that the CLI cannot handle correctly (returns error 2006). **Always use the SDK for these endpoints.**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/payments/links/orders` | Create a payment link (creates a new order inline — does NOT accept an existing order_id) |
| POST | `/payments/links/refunds` | Create a payment link for a refund |

### `POST /payments/links/orders` — `business_info` schema

`business_info` embeds the full order creation parameters. Required fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `merchant_id` | string | ✅ | e.g. `M1017` |
| `psp_order_code` | string | ✅ | Unique reference code you assign |
| `pricing_currency` | string | ✅ | `USD`, `USDT`, or `USDC` |
| `pricing_amount` | string | ✅ | Base amount (2 decimal places, e.g. `"1000.00"`) |
| `fee_amount` | string | ✅ | Developer fee (e.g. `"200.00"`) |
| `payable_currencies` | string[] | ✅ | e.g. `["TRON_USDT"]` — note: array, not a single string |
| `expired_in` | int | | Seconds until expiry (default 1800, max 10800) |
| `amount_tolerance` | string | | Allowed underpayment (e.g. `"0.5"`) |

> For a complete SDK example, see `recipes.md` Recipe 8.

---

## Exchange Rates & Tokens

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/payments/exchange_rates` | List all exchange rates |
| GET | `/payments/exchange_rates/{token_id}/{currency}` | Rate for specific token/fiat pair |
| GET | `/payments/supported_tokens` | List tokens supported for payment |
