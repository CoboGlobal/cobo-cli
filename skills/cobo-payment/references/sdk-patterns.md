# Payment SDK Patterns

Uses the same `cobo_waas2` SDK as WaaS. Payment endpoints are accessed via `PaymentApi`.

## When to Use CLI vs SDK

| Scenario | Use |
|----------|-----|
| Quick queries, exploration | CLI |
| One-off operations | CLI |
| Production order processing | SDK |
| Webhook handlers | SDK |
| Automation / batch operations | SDK |

## Environment Setup

```bash
# macOS / Linux
eval $(cobo config env)

# Windows PowerShell
cobo config env --format powershell | Invoke-Expression
```

## Language Templates

Load the template for the target language:

| Language | Template |
|----------|----------|
| Python | `assets/templates/python.md` |
| TypeScript / Node.js | `assets/templates/ts-node.md` |
| Go | `assets/templates/go.md` |
| Java | `assets/templates/java.md` |

Each template contains: setup block, list orders, create order, create payout, and language-specific patterns (error handling, polling). Follow the template style exactly — keep snippets concise.

## Endpoints That Require SDK (CLI Not Supported)

These endpoints use complex nested request bodies that the CLI cannot serialize correctly (returns error 2006). **Always use the SDK:**

| Endpoint | Reason |
|----------|--------|
| `POST /payments/links/orders` | `business_info` is a nested object with array fields |
| `POST /payments/links/refunds` | Same — `business_info` nested structure |

See `references/recipes.md` Recipe 8 for a complete payment link example.
