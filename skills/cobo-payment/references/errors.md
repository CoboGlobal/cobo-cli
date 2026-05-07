# Payment Errors & Recovery

## Debug Commands

```bash
cobo --enable-debug get /payments/orders   # Show full request/response
cobo config list                           # Check current config
cobo doc /payments/orders                  # Check endpoint parameters
cobo logs tail                             # Recent API logs
```

## HTTP Status Recovery

| HTTP Status | Description | Quick Fix |
|-------------|-------------|-----------|
| 200 | Success | No action needed |
| 400 | Bad Request | Check request parameters: `cobo doc /payments/<path>` |
| 401 | Unauthorized | Check API Key and signature. `cobo keys generate --key-type API` + `cobo keys register` (dev) or Portal (prod) |
| 403 | Forbidden | Check key permissions: `cobo open developer` → add Payment permissions |
| 404 | Not Found | Verify endpoint: `cobo get --list \| grep payments` |
| 405 | Method Not Allowed | Use correct HTTP method (GET/POST) for this endpoint |
| 406 | Not Acceptable | Ensure request content is JSON |
| 429 | Too Many Requests | Reduce request frequency and retry later |
| 500 | Internal Server Error | Check Org Access Token expiry, then retry |
| 502 | Bad Gateway | Check connection and retry later |
| 503 | Service Unavailable | Retry later |

## Business Error Codes

When the response includes an `error_code` field, use these specific recovery steps:

| error_code | Description | Solution |
|------------|-------------|----------|
| 1000 | Internal server error (may include Org Access Tokens expired) | Check server config, verify Org Access Tokens, retry |
| 1003, 2003 | Missing required parameters | Check `cobo doc /payments/<path>` for required fields |
| 1006, 2006 | Invalid parameter format or unsupported values | Provide valid parameters in expected format |
| 2000 | Internal error during processing | Retry later |
| 2002 | Unsupported HTTP method | Use supported HTTP method for this endpoint |
| 2010 | Rate limit exceeded | Retry later |
| 2022 | Missing required request headers | Include all required headers |
| 2023 | API signature missing or invalid | Verify API signature is correct |
| 2024 | API Key authentication failed | 1. Use API Key matching current env (dev/prod) 2. Ensure key is registered and active 3. Permanent keys require whitelisted IP. Register: `cobo keys register` (dev) or `cobo open developer` (prod) |
| 2025, 4001 | Forbidden — no permission for resource | Add Payment permission to API key: `cobo open developer` |
| 2026 | Too many requests | Retry later |
| 2028 | Requested resource not found | Check request URL and resource ID |
| 2029 | Invalid status attribute | Provide valid value for status filter |
| 2040 | Resource with same key already exists | Use unique key |
| 2050, 2052 | No available plan or usage limit exceeded | Purchase or upgrade plan |
| 2051 | Current plan expired | Renew plan |
| 30001, 12009 | Duplicate request_id | Generate new unique request_id: `order-$(date +%s)-$(openssl rand -hex 4)` |
| 30007 | Invalid amount (wrong format or range) | Use decimal string e.g. `"100.00"`, not integer |
| 30008 | Invalid absolute amount (too small, too large, or zero) | Ensure amount meets required conditions |
| 30010 | Amount below dust threshold | Increase amount to exceed dust threshold |
| 30011 | Amount below minimum deposit threshold | Increase deposit amount |
| 30012, 12007 | Insufficient balance | Ensure source account has sufficient balance |
| 30013 | Insufficient balance for transaction fees | Ensure source has enough for amount + fees |
| 30014 | Invalid destination address | Provide valid address for the chain |
| 60010 | Token not enabled for this team | Enable token in Portal settings |
| 12002 | Token not supported by Cobo | Check `/payments/supported_tokens` for valid tokens |

## Payment-Specific Issues

### Order Not Receiving Payment
```bash
# Verify order is still active (not Expired)
cobo get /payments/orders/$ORDER_ID

# Check receive_address was shown to payer
# Verify correct chain and token

# If expired, create new order
REQUEST_ID="order-$(date +%s)-$(openssl rand -hex 4)"
cobo post /payments/orders --request_id "$REQUEST_ID" ...
```

### Underpaid Order
```bash
# Check order status and payable_amount vs received
cobo get /payments/orders/$ORDER_ID

# Options:
# 1. Accept underpayment (if within tolerance)
# 2. Ask payer to send the difference
# 3. Issue partial refund of received amount
```

### Payout Rejected by Bank (OffRamp)
```bash
# Get payout details
cobo get /payments/payouts/$PAYOUT_ID

# status: RejectedByBank
# Check recipient_info for bank details
# Verify counterparty_entry is correct
cobo get /payments/counterparty_entry/$ENTRY_ID

# Contact support: help@cobo.com
```

### Refund Address Not Submitted (AddressPending)
```bash
# Status stays AddressPending when to_address not provided at creation
# Payer must submit address via the refund link
cobo get /payments/refunds/$REFUND_ID
# Check refund_link field in response — share with payer
```

### Insufficient Balance for Payout
```bash
# Check merchant balance
cobo get /payments/balance/merchants --merchant_id M1001

# Check PSP balance for developer-source payouts
cobo get /payments/balance/psp

# Ensure pending orders complete before payout
cobo get /payments/orders --merchant_id M1001 --statuses Processing
```

## Common error_code Combinations

- **1003, 2003** — Missing required params (check `cobo doc`)
- **1006, 2006** — Invalid param format
- **30001, 12009** — Duplicate request_id (generate new one)
- **2025, 4001** — Permission denied (add Payment permission)
