import random
from web3 import Web3
from utils.utils import read_json
from utils.models import ChainExplorers
from ..config import CONFIG
from ..paths import UNICHAIN_BRIDGE_ABI


class UnichainBridge:
    def __init__(self, client, logger, db_manager, session):
        self.client = client
        self.session = session
        self.db_manager = db_manager
        self.contract = self.client.w3.eth.contract(
            address='0xe8CDF27AcD73a434D661C84887215F7598e7d0d3', 
            abi=read_json(UNICHAIN_BRIDGE_ABI)
        )
        self.logger = logger
        self.explorer = ChainExplorers.OPTIMISM.value

    async def get_balance(self):
        balance_wei = await self.client.w3.eth.get_balance(self.client.address)
        return self.client.w3.from_wei(balance_wei, 'ether')

    async def quote_send_fee(self, send_param):
        try:
            fee = await self.contract.functions.quoteSend(send_param, False).call()
            return fee
        except Exception as e:
            self.logger.error(f"Failed to quote send fee: {e}")
            raise

    async def bridge(self, amount_eth):
        try:
            amount_wei = self.client.w3.to_wei(amount_eth, 'ether')
            send_param = (
                30320,
                self.client.w3.to_bytes(hexstr=self.client.address).rjust(32, b'\0'),
                amount_wei,
                int(amount_wei * 0.95),
                b'',
                b'',
                b''
            )

            native_fee, lz_token_fee = await self.quote_send_fee(send_param)
            total_value = amount_wei + native_fee

            balance_eth = await self.get_balance()
            if balance_eth < self.client.w3.from_wei(total_value, 'ether'):
                self.logger.error("Insufficient ETH balance for bridging!")
                return False, None

            self.logger.info(f"Bridging {amount_eth:.7f} ETH from Optimism to Unichain...")
            transaction = await self.contract.functions.send(
                send_param,
                (native_fee, lz_token_fee),
                self.client.address
            ).build_transaction({
                'chainId': await self.client.w3.eth.chain_id,
                'from': self.client.address,
                'value': total_value,
                'gasPrice': int(await self.client.w3.eth.gas_price * 1.1),
                'nonce': await self.client.w3.eth.get_transaction_count(self.client.address),
            })

            transaction['gas'] = await self.client.w3.eth.estimate_gas(transaction)

            signed_txn = self.client.w3.eth.account.sign_transaction(transaction, self.client.key)
            tx_hash = await self.client.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            self.logger.info(f"Bridge transaction sent: {self.explorer}{tx_hash.hex()}")

            receipt = await self.client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt['status'] == 1:
                self.logger.info("Bridge transaction confirmed successfully!")
                return True, tx_hash.hex()
            else:
                self.logger.error("Bridge transaction failed on-chain!")
                return False, tx_hash.hex()

        except Exception as e:
            self.logger.error(f"Bridge failed: {e}")
            return False, None

    async def run(self):
        try:
            random_bridge_amount = round(random.uniform(*CONFIG.UNICHAIN_BRIDGE.BRIDGE_AMOUNT), 7)
            self.logger.info(f"Preparing to bridge {random_bridge_amount:.7f} ETH...")
            status, tx_hash = await self.bridge(random_bridge_amount)
            if status:
                self.logger.info("Bridge successful!")
                self.logger.success(f"Bridge successful: {self.explorer}{tx_hash}")
            else:
                self.logger.error("Bridge failed!")
        except Exception as e:
            self.logger.error(f"Run failed: {e}")
