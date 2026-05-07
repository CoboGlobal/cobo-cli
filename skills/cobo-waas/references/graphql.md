# GraphQL usage (advanced)

## Basic usage
- Inline query (JSON with query key):
  `cobo graphql -q '{"query":"{ wallet(walletId:<WALLET_ID>) { walletId name } }"}'`

## With variables
- Query:
  `cobo graphql -q 'query($id:String!){ wallet(walletId:$id){ walletId name } }' -v '{"id":"<WALLET_ID>"}'`

## From file
- Save a query in `query.graphql` and run:
  `cobo graphql -f ./query.graphql -v '{"id":"<WALLET_ID>"}'`

## Output formatting
- Raw JSON output:
  `cobo graphql -q '{"query":"{ wallet(walletId:<WALLET_ID>) { walletId name } }"}' --raw`

## Tips
- Ensure auth and env are set (`cobo auth ...`, `cobo env ...`).
- If a query fails, add `--enable-debug` to see request details.
