from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import yaml
from pathlib import Path
import asyncio

@dataclass
class WithdrawalConfig:
    currency: str
    networks: List[str]
    min_amount: float
    max_amount: float
    wait_for_funds: bool
    max_wait_time: int
    retries: int
    max_balance: float

@dataclass
class ExchangesConfig:
    name: str
    apiKey: str
    secretKey: str
    passphrase: str
    withdrawals: List[WithdrawalConfig]

@dataclass
class Config:
    EXCHANGES: ExchangesConfig
    @classmethod
    def load(cls, path: str = "D:\\Optimistic soft\\Optisoft\\run_optisoft\\cex_yaml.yaml") -> "Config":
        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return cls(
            EXCHANGES=ExchangesConfig(
                name=data["EXCHANGES"]["name"],
                apiKey=data["EXCHANGES"]["apiKey"],
                secretKey=data["EXCHANGES"]["secretKey"],
                passphrase=data["EXCHANGES"]["passphrase"],
                withdrawals=[
                    WithdrawalConfig(
                        currency=w["currency"],
                        networks=w["networks"],
                        min_amount=w["min_amount"],
                        max_amount=w["max_amount"],
                        wait_for_funds=w["wait_for_funds"],
                        max_wait_time=w["max_wait_time"],
                        retries=w["retries"],
                        max_balance=w["max_balance"]) for w in data["EXCHANGES"]["withdrawals"]]))

def get_config() -> Config:
    if not hasattr(get_config, "_config"):
        get_config._config = Config.load()
    return get_config._config