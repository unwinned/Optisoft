CEX_WITHDRAWAL_RPCS = {
    "Arbitrum": "https://arb1.lava.build",
    "Optimism": "https://optimism.lava.build",
    "Base": "https://base.lava.build",
}

NETWORK_MAPPINGS = {
    "okx": {
        "Arbitrum": "ARBONE",
        "Base": "Base",
        "Optimism": "OPTIMISM"
    },
    "bitget": {
        "Arbitrum": "ARBITRUMONE",
        "Base": "BASE",
        "Optimism": "OPTIMISM"
    }
}

EXCHANGE_PARAMS = {
    "okx": {
        "balance": {"type": "trading"},
        "withdraw": {"pwd": ""}
    },
    "bitget": {
        "balance": {},
        "withdraw": {}
    }
}


SUPPORTED_EXCHANGES = ["okx"]