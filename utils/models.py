import re
from enum import Enum


class Proxy:
    def __init__(self, proxy: str | None):
        self.proxy = proxy
        self.validate()

    def __bool__(self):
        return bool(self.proxy)

    @property
    def session_proxy(self):
        if self.proxy:
            return {
                'http': f'http://{self.proxy}',
                'https': f'http://{self.proxy}'
            }

    @property
    def w3_proxy(self):
        if self.proxy:
            return f'http://{self.proxy}'

    def __getattr__(self, item):
        return self.__dict__[item] if self.__dict__['proxy'] else None

    def validate(self):
        if self.proxy:
            pattern = r'^.+:.+@.+:\d+$'
            if not re.fullmatch(pattern, self.proxy):
                raise ValueError('Proxy format is not valid', self.proxy)

    def __repr__(self):
        return f'Proxy <{self.proxy}>' if self.proxy else 'No proxy found'


class RpcProviders(Enum):
    BSC = 'https://rpc.ankr.com/bsc/a27491f5239db00f57a99fbf3ff085e564d763a789cec167f635c3202c29ad7a'
    OPTIMISM = "https://1rpc.io/op"
    UNICHAIN = "https://unichain.drpc.org"
    ARBITRUM = "https://rpc.ankr.com/arbitrum"
    BASE = "https://rpc.ankr.com/base"


class ChainExplorers(Enum):
    OPTIMISM = "https://optimistic.etherscan.io/tx/"
    UNICHAIN = "https://uniscan.xyz/tx/"
    BASE = "https://basescan.org/tx/"
    ARBITRUM = "https://arbiscan.io/tx/"


class TxStatusResponse(Enum):
    NEED_APPROVE = 'NEED_APPROVE'
    GOOD = 'GOOD'
    COOLDOWN_PERIOD = 'COOLDOWN_PERIOD'
    ALREADY_MINTED = 'ALREADY_MINTED'
    GAS_WARNING = 'GAS_WARNING'
    STATUS_ZERO = 'STATUS_ZERO'
    INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE'
    FAILED = 'FAILED'
