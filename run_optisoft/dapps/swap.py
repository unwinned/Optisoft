from decimal import Decimal
from utils.utils import approve_asset, asset_balance, generate_simple_abi, read_json, approve_if_insufficient_allowance
from utils.models import ChainExplorers, RpcProviders
from .constants import UNISWAP_CONTRACT, UNISWAP_TOKENS, PERMIT_CONTRACT, VELODROME_CONTRACT
from ..config import CONFIG
from ..paths import UNISWAP_ROUTER_ABI, PERMIT_ABI
import random
import time


class Uniswap:
    def __init__(self, client, session, logger, db_manager):
        self.client = client
        self.session = session
        self.logger = logger
        self.db_manager = db_manager
        self.explorer = ChainExplorers.UNICHAIN.value
        

    async def check_balance(self):
        self.contract = self.client.w3.eth.contract(
            address=VELODROME_CONTRACT, abi=read_json(UNISWAP_ROUTER_ABI)
        )
        
        self.permit_contract = self.client.w3.eth.contract(
            address=PERMIT_CONTRACT, abi=read_json(PERMIT_ABI)
        )
        
        balance = await asset_balance(self, UNISWAP_TOKENS["USDT0"]["address"])
        balance_in_eth = self.client.w3.from_wei(balance, 'ether')
        
        demo = await self.client.w3.eth.get_balance(self.client.address)
        balance_of_eth = self.client.w3.from_wei(demo, 'ether')
        
        self.logger.info(f"Balance of USDT is: {balance_in_eth} and ETH is: {balance_of_eth}")
        return balance_of_eth
        
        
    async def amount_to_swap(self, balance_of_eth):
        self.logger.info("Calculating amount to swap. Please, wait some time.")
        
        percentage = random.randint(*CONFIG.UNISWAP.SWAP_AMOUNT_PERCENTAGE)
        self.logger.debug(percentage)

        balance_wei = self.client.w3.to_wei(balance_of_eth, 'ether')
        self.logger.debug(balance_wei)
        
        balance_wei_percentage = (balance_wei * percentage) // 100
        self.logger.debug(balance_wei_percentage)
        
        balance_ether_percentage = self.client.w3.from_wei(balance_wei_percentage, 'ether')
        self.logger.debug(balance_ether_percentage)
        
        balance_wei_reduced = (balance_wei_percentage * 95) // 100
        self.logger.debug(balance_wei_reduced)
                
        self.logger.info(f"Getting started to swap: {self.client.w3.from_wei(balance_wei_reduced, 'ether')} ETH and {balance_wei_percentage}")
        return balance_wei_reduced
        
        
    async def run(self):
        self.client.define_new_provider(RpcProviders.UNICHAIN.value, 130)
        # await self.amount_to_swap(await self.check_balance())
        await self.prepare_data(await self.amount_to_swap(await self.check_balance()))
        
    async def prepare_data(self, balance_wei_reduced):
        if balance_wei_reduced == 0:
            self.logger.error("Amount to swap is 0, cannot perform swap")
            return
        try:
            if not CONFIG.UNISWAP.SWAP_ALL_TO_ETH:
                recipient = self.client.address
                amount_in = balance_wei_reduced
                amount_out_min = 0
                token_in = "0x4200000000000000000000000000000000000006"
                token_out = "0x9151434b16b9763660705744891fA906F660EcC5"
                fee_options = [3000, 500, 10000, 300]
                
                for fee in fee_options:
                        path = (self.client.w3.to_bytes(hexstr=token_in.replace("0x", "")) + fee.to_bytes(3, "big") + 
                                self.client.w3.to_bytes(hexstr=token_out.replace("0x", "")))
                
                payer_is_user = True

                inputs = self.client.w3.codec.encode(
                ["address", "uint256", "uint256", "bytes", "bool"],
                [recipient, amount_in, amount_out_min, path, payer_is_user])

                inputs_array = [inputs]
                command = bytes.fromhex('00') 
                deadline = int(time.time()) + 1200
            
                method = self.contract.functions.execute(
                    command,
                    inputs_array,
                    deadline
                )
                
                await approve_asset(self.contract, token_in, self.client.address, amount_in)
                await method.call()
        except Exception as e:
            raise e
        finally:
            self.logger.success("Call passed successfully")
            
            # tx = await method.build_transaction({
            # 'from': self.client.address,
            # 'nonce': await self.client.w3.eth.get_transaction_count(self.client.address),
            # 'gas': 200000,
            # 'maxFeePerGas': self.client.w3.to_wei(50, 'gwei'),
            # 'maxPriorityFeePerGas': self.client.w3.to_wei(2, 'gwei'),
            #  })
            # signed_tx = self.client.w3.eth.account.sign_transaction(tx, private_key=self.client.key)
            # tx_hash = await self.client.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            # receipt = await self.client.w3.eth.wait_for_transaction_receipt(tx_hash)
            # self.logger.success(f"Transaction successfull: {self.explorer}{tx_hash}")