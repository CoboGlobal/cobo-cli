# API Quick Reference

Get full Cobo WaaS 2.0 endpoint and description from [LLM](https://www.cobo.com/developers/llms.txt)

Use `cobo <method> --list` for full endpoint list.

## Endpoint Discovery

```bash
# List all GET endpoints
cobo get --list

# List all POST endpoints
cobo post --list

# Describe endpoint parameters
cobo post /wallets --describe

# Describe specific parameter
cobo post /wallets --describe --wallet_type

# Open API docs
cobo doc /wallets
```
