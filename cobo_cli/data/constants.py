supported_wallet_type_choices = [
    "custodial-asset",
    "custodial-web3",
    "mpc-org-controlled",
    "mpc-user-controlled",
    "smart-contract",
    "exchange",
]


def convert_wallet_type(wallet_type: str) -> str:
    mapper = {
        supported_wallet_type_choices[0]: "custodial-asset",
        supported_wallet_type_choices[1]: "custodial-web3",
        supported_wallet_type_choices[2]: "mpc-org-controlled",
        supported_wallet_type_choices[3]: "mpc-user-controlled",
        supported_wallet_type_choices[4]: "smart-contract",
        supported_wallet_type_choices[5]: "exchange",
    }
    return mapper[wallet_type]
