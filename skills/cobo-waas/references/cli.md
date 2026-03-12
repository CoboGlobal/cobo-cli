# CLI command patterns

## Preflight
- Check version: `cobo version`
- Check config: `cobo config list`
- Set environment: `cobo env sandbox|dev|prod`
- Set auth method: `cobo auth apikey|user|org|none`
- Get help: `cobo --help` or `cobo <subcommand> --help`

## Discover endpoints
- **Look up parameters before generating code (recommended):** `cobo doc /path` — e.g. `cobo doc /wallets` prints parameter names, types, and requirements for that path; use this output to build correct `cobo get/post` or SDK calls.
- List operations: `cobo get --list`, `cobo post --list`, `cobo put --list`, `cobo delete --list`
- Describe an endpoint: `cobo get /path --describe` or `cobo post /path --describe`
- Describe specific parameters: `cobo get /path --describe --param_name`
- Open docs: `cobo doc` (browser) or `cobo doc /path` (print API details for path)

## Call APIs (WaaS 2.0)
- GET: `cobo get /path --param value`
- POST: `cobo post /path --param value`
- PUT: `cobo put /path --param value`
- DELETE: `cobo delete /path --param value`

## Keys
- Generate API keypair: `cobo keys generate --key-type API`
- Register API key (dev/sandbox only): `cobo keys register` (uses api_key from config) or `cobo keys register --pubkey <hex>`
- Validate keypair: `cobo keys validate --alg ed25519 --secret <hex> --pubkey <hex>`

## GraphQL (advanced)
- Inline query: `cobo graphql -q '{ wallets { wallet_id name } }'`
- With variables: `cobo graphql -q 'query($id:String!){ wallet(wallet_id:$id){ name } }' -v '{\"id\":\"<WALLET_ID>\"}'`
- From file: `cobo graphql -f ./query.graphql -v '{\"id\":\"<WALLET_ID>\"}'`
- Raw output: `cobo graphql -q '{ ... }' --raw`

## Logs and webhooks
- Tail logs: `cobo logs tail`
- Filter logs: `cobo logs tail --http-method POST --request-path /v2/transactions`
- Webhook events: `cobo webhook events`
- Listen: `cobo webhook listen --events "wallets.transaction.succeeded"`
- Trigger test: `cobo webhook trigger wallets.transaction.succeeded`

## Portal links
- Open portal: `cobo open portal`
- Open developer console: `cobo open developer`
- Open wallets page: `cobo open wallets`

## Debugging
- Enable debug: `cobo --enable-debug get /wallets`
