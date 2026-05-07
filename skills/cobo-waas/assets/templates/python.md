# Python SDK Sample (WaaS 2.0)

## Installation

```bash
pip install cobo-waas2
```

## Environment (all languages)

Load env from cobo config, then run your script:

- **macOS / Linux:** `eval $(cobo config env)`
- **Windows PowerShell:** `cobo config env --format powershell | Invoke-Expression`
- **Windows CMD:** `cobo config env --format cmd > env.bat && env.bat`

## Setup

```python
import os
from cobo_waas2 import Configuration, ApiClient
from cobo_waas2.api import WalletsApi

api_secret = os.environ["COBO_API_SECRET"]
env = os.environ.get("COBO_ENV", "dev")

config = Configuration(
    api_private_key=api_secret,
    host=f"https://api.{env}.cobo.com/v2" if env != "prod" else "https://api.cobo.com/v2",
)
client = ApiClient(config)
wallets_api = WalletsApi(client)
```

## List Wallets

```python
response = wallets_api.list_wallets(limit=10)
for w in response.data:
    wallet = w.actual_instance
    print(f"{wallet.wallet_id}: {wallet.name}")
```

## Create Custodial Wallet

```python
from cobo_waas2.models import CreateWalletParams, CreateCustodialWalletParams, WalletType, WalletSubtype

# IMPORTANT: Must wrap params with CreateWalletParams(actual_instance=...)
params = CreateWalletParams(actual_instance=CreateCustodialWalletParams(
    name="My Wallet",
    wallet_type=WalletType.CUSTODIAL,
    wallet_subtype=WalletSubtype.ASSET
))

response = wallets_api.create_wallet(create_wallet_params=params)
wallet = response.actual_instance  # IMPORTANT: Use .actual_instance
print(f"Created: {wallet.wallet_id}")
```

## Create MPC Wallet

```python
from cobo_waas2.api import WalletsMpcWalletsApi
from cobo_waas2.models import CreateWalletParams, CreateMpcWalletParams, WalletType, WalletSubtype

# Get vault_id first (endpoint: /wallets/mpc/vaults)
mpc_api = WalletsMpcWalletsApi(client)
vaults = mpc_api.list_mpc_vaults("Org-Controlled")
vault_id = vaults.data[0].vault_id

params = CreateWalletParams(actual_instance=CreateMpcWalletParams(
    name="MPC Wallet",
    wallet_type=WalletType.MPC,
    wallet_subtype=WalletSubtype.ORG_CONTROLLED,
    vault_id=vault_id
))

response = wallets_api.create_wallet(create_wallet_params=params)
wallet = response.actual_instance
print(f"Created: {wallet.wallet_id}")
```

## Create Address

```python
# IMPORTANT: Requires 'count' param, returns a LIST
response = wallets_api.create_address(
    wallet_id=wallet.wallet_id,
    create_address_request=CreateAddressRequest(chain_id="ETH", count=1)
)
address = response.data[0]  # Response is a list
print(f"Address: {address.address}")
```

## Create Transfer

```python
import time
from cobo_waas2.api import TransactionsApi
from cobo_waas2.models import TransferParams, TransferSource, TransferDestination, WalletSubtype, CustodialTransferSource, AddressTransferDestination, AddressTransferDestinationAccountOutput

tx_api = TransactionsApi(client)

params = TransferParams(
    request_id=f"tx-{int(time.time())}-{os.urandom(4).hex()}",
    source=TransferSource(
        actual_instance=CustodialTransferSource(
            source_type=WalletSubtype.ASSET, 
            wallet_id=wallet.wallet_id
        )
    ),
    token_id="ETH",
    destination=TransferDestination(
        actual_instance=AddressTransferDestination(
            destination_type="Address",
            account_output=AddressTransferDestinationAccountOutput(
                address="0x...", 
                amount="0.01"
            )
        )
    )
)

response = tx_api.create_transfer_transaction(transfer_params=params)
tx = response.actual_instance
print(f"TX: {tx.transaction_id}, Status: {tx.status}")
```

## List Webhook Events

```python
from cobo_waas2.api import DevelopersWebhooksApi

webhooks_api = DevelopersWebhooksApi(client)
# NOTE: Returns list directly, not .data
events = webhooks_api.list_webhook_event_definitions()
for e in events:
    print(f"{e.event_type}")
```

## Error Handling

```python
from cobo_waas2.exceptions import ApiException

try:
    response = wallets_api.list_wallets()
except ApiException as e:
    print(f"Error {e.status}: {e.body}")
```

---

## Required Permissions

| Operation | Permission |
|-----------|------------|
| List/Get wallets | Wallet - Read |
| Create wallet | Wallet - Write |
| Create address | Address - Write |
| Create transfer | Transaction - Write |
| Webhooks | Webhook - Read/Write |

Configure in Portal: `cobo open developer`
