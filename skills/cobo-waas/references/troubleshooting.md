# Troubleshooting Decision Tree

Visual troubleshooting guide organized by symptom. Follow the tree to diagnose and resolve issues.

---

## CLI Not Working

```
cobo command fails?
│
├── "command not found: cobo"
│   └── CLI not installed
│       → pip install cobo-cli
│       → Verify: cobo version
│
├── "ModuleNotFoundError"
│   └── Broken installation
│       → pip uninstall cobo-cli
│       → pip install cobo-cli
│
├── "Permission denied"
│   └── Installation permission issue
│       → pip install --user cobo-cli
│       → Or use virtualenv
│
└── Version mismatch or old version
    └── Update CLI
        → pip install --upgrade cobo-cli
```

---

## Configuration Issues

```
cobo config list shows problems?
│
├── Empty or no output
│   └── Fresh installation
│       → cobo env dev
│       → cobo keys generate --key-type API
│       → cobo auth apikey
│
├── Missing env
│   └── Environment not set
│       → cobo env dev  # or prod, sandbox
│
├── Missing auth_method
│   └── Auth method not set
│       → cobo auth apikey
│
├── Missing api_key or api_secret
│   └── Keys not generated
│       → cobo keys generate --key-type API
│       → Save the output!
│
└── Wrong environment
    └── Pointing to wrong env
        → cobo env <correct_env>
        → Register keys in that environment's Portal
```

---

## API Calls Failing

```
cobo get/post returns error?
│
├── Connection error / timeout
│   ├── No internet
│   │   → Check network connectivity
│   │
│   ├── VPN/proxy issue
│   │   → Disable VPN or configure proxy
│   │
│   └── Firewall blocking
│       → Allow api.cobo.com, api.dev.cobo.com
│
├── Status 400 Bad Request
│   ├── Missing required parameter
│   │   → cobo <method> /path --describe
│   │
│   ├── Invalid parameter value
│   │   → cobo <method> /path --describe --param_name
│   │
│   └── Malformed JSON
│       → Check JSON syntax in complex params
│       → Use single quotes around JSON
│
├── Status 401 Unauthorized
│   ├── No keys in config
│   │   → cobo config list
│   │   → cobo keys generate --key-type API
│   │
│   ├── Keys not registered in Portal
│   │   → cobo open developer
│   │   → Add public key as API key
│   │
│   ├── Auth method not set
│   │   → cobo auth apikey
│   │
│   └── Wrong environment for key
│       → Key registered in dev but calling prod?
│       → cobo env <correct_env>
│
├── Status 403 Forbidden
│   ├── Insufficient key permissions
│   │   → cobo open developer
│   │   → Edit key → Add permissions
│   │
│   ├── Resource not owned by org
│   │   → Check resource belongs to your org
│   │
│   └── Operation not allowed
│       → Check if wallet type supports operation
│
├── Status 404 Not Found
│   ├── Wrong endpoint path
│   │   → cobo get --list | grep <keyword>
│   │
│   ├── Resource doesn't exist
│   │   → cobo get /wallets (list resources)
│   │
│   └── Wrong environment
│       → Resource in dev but querying prod?
│
├── Status 409 Conflict
│   └── Duplicate request_id
│       → Use unique request_id:
│         --request_id "tx-$(date +%s)-$(openssl rand -hex 4)"
│
├── Status 429 Rate Limited
│   └── Too many requests
│       → Wait and retry
│       → Add delays between requests
│
└── Status 500/502/503
    └── Server issue
        → Wait 30-60 seconds
        → Retry request
        → Check Cobo status page [Error codes](https://www.cobo.com/developers/v2/guides/overview/error-codes.md)
```

## Quick Diagnosis Commands

Run these to quickly assess state:

```bash
# Full diagnostic
echo "=== CLI ===" && cobo version
echo "=== Config ===" && cobo config list
echo "=== Connectivity ===" && cobo get /wallets --limit 1 2>&1 | head -3

# Specific checks
cobo config list | grep env          # Check environment
cobo config list | grep auth_method  # Check auth
cobo get --list | head -10           # Verify API access
```

---

## When to Escalate

Contact Cobo support if:

1. **500 errors persist** after retries
4. **Unexplained 403** with correct permissions
5. **Data inconsistency** between API and Portal

Include in support request:
- Environment (dev/prod/sandbox)
- Command with `--enable-debug` output
- Error message
- Organization Id
- Transaction/wallet IDs (if applicable)
