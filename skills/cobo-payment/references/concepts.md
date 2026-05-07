# Payment Concepts & Glossary

## Core Roles

| Role | Description |
|------|-------------|
| **PSP** (Payment Service Provider) | The developer/organization operating the payment platform |
| **Merchant** | A business entity that accepts payments through the PSP |
| **Payer** | The end customer making a payment |

## Key Objects

### Order (Pay-in)
A request for a payer to send cryptocurrency to a merchant. Created by the PSP on behalf of the merchant.

- `order_id` — Cobo-generated ID
- `merchant_order_code` — Merchant's own reference (provided by merchant)
- `psp_order_code` — PSP's own reference (provided by developer)
- `pricing_currency` — Fiat currency (e.g. USD, EUR)
- `pricing_amount` — Fiat amount to charge (excluding fee)
- `fee_amount` — Developer fee added on top
- `payable_currency` — Crypto token for payment (e.g. USDT)
- `payable_amount` — Crypto amount to pay (if not provided, calculated from exchange rate)
- `receive_address` — Crypto address payer should send to
- `amount_tolerance` — Allowed underpayment tolerance (e.g. 0.5 means ±0.5 of payable_amount)

**Order statuses:**
| Status | Meaning |
|--------|---------|
| `Pending` | Created, awaiting payment |
| `Underpaid` | Payment received but less than required |
| `Processing` | Payment received, confirming on-chain |
| `Completed` | Payment confirmed |
| `Expired` | Order expired without full payment |
| `Failed` | Payment failed |

### Refund
Return of funds to a payer for a completed pay-in order.

- `refund_id` — Cobo-generated ID
- `order_id` — The pay-in order being refunded
- `to_address` — Crypto address to refund to (provided by payer)
- `amount` — Crypto amount to refund

**Refund statuses:** `AddressPending` → `AddressSubmitted` → `Pending` → `Processing` → `Completed` / `Failed`

### Payout
Settlement payment from a merchant or PSP account to a counterparty (crypto address or bank account).

- `payout_id` — Cobo-generated ID
- `payout_channel` — `Crypto` (on-chain transfer) or `OffRamp` (fiat bank transfer)
- `source_account` — Merchant ID (e.g. `M1001`) or `"developer"` for PSP account
- `payout_items` — List of individual payout instructions

**Payout statuses:** `Pending` → `Preparing` → `Transferring` → `Completed` / `PartiallyCompleted` / `Failed` / `RejectedByBank`

### Merchant
A business entity with its own balance and wallet configuration.

- `merchant_id` — Unique ID (e.g. `M1001`)
- `wallet_setup`:
  - `Shared` — Shares wallets with other merchants (cost-efficient)
  - `Separate` — Dedicated wallet, full fund isolation
  - `Default` — System-created default merchant (same name as organization)

### Counterparty
An external entity that can receive payouts.

- Used for managing crypto wallet addresses of external entities (API only supports wallet addresses)
- `counterparty_id` — Cobo-generated ID
- `counterparty_entry` — Wallet address entry under a counterparty (bank accounts NOT supported via API)

### Destination
A registered payout destination (crypto address or bank details).

- Supports both wallet addresses AND bank accounts (SWIFT/IBAN) via API
- Can be linked to a specific merchant via `merchant_id`
- `destination_id`, `destination_entry_id`

### Allocation
Distribution of received funds across multiple merchants or accounts.

- `batch_allocation_id` — ID for a batch allocation operation
- `allocation_items` — Individual allocation line items

## Wallet Setup for Payments

Payments use Custodial Web3 wallets. The wallet holds funds on behalf of merchants.

- `payment_wallet` — The wallet associated with a merchant (via `/payments/balance/payment_wallets`)
- Addresses are assigned per-order or per-merchant depending on wallet_setup

## Exchange Rates

- `/payments/exchange_rates` — List all rates
- `/payments/exchange_rates/{token_id}/{currency}` — Rate for specific token/fiat pair
- Rates are used when `payable_amount` is not specified in order creation
