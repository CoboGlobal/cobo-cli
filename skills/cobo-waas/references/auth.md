# Auth and key setup

## API key workflow (apikey auth)
1) Generate keypair:
   `cobo keys generate --key-type API`

2) Register the public key:
   - **CLI (dev/sandbox):** `cobo keys register` (requires `cobo login --user` first)
   - **Portal (all envs):** `cobo open developer` → Add the public key as an API key.

3) Set auth method:
   `cobo auth apikey`

4) Confirm config:
   `cobo config list`

## User auth (portal access)
- Login as user: `cobo login --user`
- Set auth method: `cobo auth user`

## Environment selection
- `cobo env sandbox|dev|prod`

## Notes
- Never print secrets in logs or agent outputs.
- If a command fails due to missing keys, re-check config and Portal registration.
