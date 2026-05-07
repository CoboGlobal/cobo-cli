# Use-case flows

## Help-first tip
- Use `cobo --help` or `cobo <subcommand> --help` whenever a command or flag is unclear.

## Configure environment and auth
1) Set environment:
   `cobo env sandbox|dev|prod`
2) Set auth method:
   `cobo auth apikey|user|org|none`
3) Verify config:
   `cobo config list`

## Keypair lifecycle
1) Generate API keys:
   `cobo keys generate --key-type API`
2) Register public key in Portal (Developer Console).
   `cobo open developer`
3) Validate keypair (optional):
   `cobo keys validate --alg ed25519 --secret <hex> --pubkey <hex>`

## Discover and describe endpoints
1) **Look up API parameters (do this before generating requests):**
   `cobo doc <path>`   e.g. `cobo doc /wallets` — shows parameters, types, required/optional for that path.
2) List operations:
   `cobo get --list` / `cobo post --list`
3) Describe an endpoint:
   `cobo get /path --describe` or `cobo post /path --describe`
4) Describe a specific parameter:
   `cobo post /wallets --describe --wallet_type`

## Wallet operations
- List wallets:
  `cobo get /wallets`
- Create wallet (confirm via --describe):
  `cobo post /wallets --name "Test Wallet" --wallet_type MPC --wallet_subtype Org-Controlled`
- Get wallet details:
  `cobo get /wallets/<wallet_id>`

## Address validation
- Validate destination address:
  `cobo get /wallets/check_address_validity --address "<ADDR>" --chain_id "<CHAIN>"`

## Create transfer
- Create transfer (confirm via --describe):
  `cobo post /transactions/transfer --request_id "tx-<ts>" --token_id "<TOKEN>" --source '{"source_type":"Wallet","wallet_id":"<ID>"}' --destination '{"destination_type":"Address","address":"<ADDR>","amount":"<AMOUNT>"}'`

## Check transfer status
- Get transaction status:
  `cobo get /transactions/<transaction_id>`

## Webhook debugging
- List event types:
  `cobo webhook events`
- Listen to events:
  `cobo webhook listen --events "wallets.transaction.succeeded"`
- Trigger a test event:
  `cobo webhook trigger wallets.transaction.succeeded`

## Inspect logs
- Tail logs:
  `cobo logs tail`
- Filter by endpoint:
  `cobo logs tail --request-path /v2/transactions`

## GraphQL queries (advanced)
- See `references/graphql.md` for templates.
