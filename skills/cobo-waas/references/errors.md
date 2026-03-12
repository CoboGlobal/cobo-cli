# Errors and Troubleshooting

Use [Error codes](https://www.cobo.com/developers/v2/guides/overview/error-codes.md) as the primary reference for error catalog with diagnosis and recovery solutions.

## Debug Commands

```bash
# Enable debug output (shows request/response details)
cobo --enable-debug get /wallets

# Check config state
cobo config list

# Validate keypair
cobo keys validate --alg ed25519 \
  --secret <hex> --pubkey <hex>

# Test connectivity
cobo get /wallets --limit 1

# Check endpoint documentation
cobo doc /wallets
```

## Getting Help

If errors persist:

1. **Enable debug**: `cobo --enable-debug <command>`
2. **Check docs**: `cobo doc /endpoint`
3. **Review logs**: `cobo logs tail`
4. **Open Portal**: `cobo open portal`
5. **Contact support**: Include error message and debug output
