import random
import ccxt.async_support as ccxt
import asyncio
from eth_account import Account
from web3 import Web3
from .cex.cex_info import (
    NETWORK_MAPPINGS,
    EXCHANGE_PARAMS,
    SUPPORTED_EXCHANGES,
    CEX_WITHDRAWAL_RPCS
)
from .cex_config import Config
from utils.utils import Logger
from typing import Dict

class CexWithdraw(Logger):
    def __init__(self, account_index: int, private_key: str, config: Config, session, client, db_manager=None):
        self.account_index = account_index
        self.private_key = private_key
        self.config = config
        self.session = session
        self.client = client
        self.db_manager = db_manager
        
        # Setup exchange based on config
        exchange_name = config.EXCHANGES.name.lower()
        if exchange_name not in SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
            
        # Initialize exchange
        self.exchange = getattr(ccxt, exchange_name)()
            
        # Setup exchange credentials
        self.exchange.apiKey = config.EXCHANGES.apiKey
        self.exchange.secret = config.EXCHANGES.secretKey
        if config.EXCHANGES.passphrase:
            self.exchange.password = config.EXCHANGES.passphrase
        
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Initialize Logger without account_index in messages
        super().__init__(self.client.address, additional={
            'pk': self.client.key,
            'proxy': self.session.proxies.get('http') if self.session else None
        })
        
        # Validate withdrawal config
        if not self.config.EXCHANGES.withdrawals:
            raise ValueError("No withdrawal configurations found")
            
        withdrawal_config = self.config.EXCHANGES.withdrawals[0]
        if not withdrawal_config.networks:
            raise ValueError("No networks specified in withdrawal configuration")
            
        # Web3 will be initialized later in withdraw()
        self.web3 = None
        self.network = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.check_auth()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.exchange.close()

    async def check_auth(self) -> None:
        """Test exchange authentication"""
        self.logger.info("Testing exchange authentication...")
        try:
            await self.exchange.fetch_currencies()
            self.logger.success("Authentication successful")
        except ccxt.AuthenticationError as e:
            self.logger.error(f"Authentication error: {str(e)}")
            await self.exchange.close()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during authentication: {str(e)}")
            await self.exchange.close()
            raise
            
    async def get_chains_info(self) -> Dict:
        """Get withdrawal networks information"""
        self.logger.info("Getting withdrawal networks data...")
        
        try:
            await self.exchange.load_markets()
            
            chains_info = {}
            withdrawal_config = self.config.EXCHANGES.withdrawals[0]
            currency = withdrawal_config.currency.upper()
            
            if currency not in self.exchange.currencies:
                self.logger.error(f"Currency {currency} not found on {self.config.EXCHANGES.name}")
                return {}
                
            networks = self.exchange.currencies[currency]["networks"]
            
            for key, info in networks.items():
                withdraw_fee = info["fee"]
                withdraw_min = info["limits"]["withdraw"]["min"]
                network_id = info["id"]
                
                self.logger.info(f"  - Network: {key} (ID: {network_id})")
                self.logger.info(f"    Fee: {withdraw_fee}, Min Amount: {withdraw_min}")
                self.logger.info(f"    Enabled: {info['withdraw']}")
                
                if info["withdraw"]:
                    chains_info[key] = {
                        "chainId": network_id,
                        "withdrawEnabled": True,
                        "withdrawFee": withdraw_fee,
                        "withdrawMin": withdraw_min
                    }
                        
            return chains_info
        except Exception as e:
            self.logger.error(f"Error getting chains info: {str(e)}")
            await self.exchange.close()
            raise

    async def wait_for_transaction(self, initial_balance: int, timeout: int = 600) -> str:
        """Wait for funds to arrive and return the transaction hash"""
        start_time = asyncio.get_event_loop().time()
        self.logger.info(f"Waiting for funds to arrive. Initial balance: {self.web3.from_wei(initial_balance, 'ether')} ETH")
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                current_balance = self.web3.eth.get_balance(self.address)
                if current_balance > initial_balance:
                    # Funds arrived; find the transaction hash
                    latest_block = self.web3.eth.block_number
                    for block_num in range(latest_block, max(latest_block - 10, 0), -1):  # Check last 10 blocks
                        block = self.web3.eth.get_block(block_num, full_transactions=True)
                        for tx in block.transactions:
                            if tx['to'] == self.address and tx['value'] > 0:
                                tx_hash = tx['hash'].hex()
                                self.logger.success(f"Funds received! Transaction hash: {tx_hash}")
                                return tx_hash
                    self.logger.success("Funds received, but transaction hash not found in recent blocks")
                    return "Unknown (funds confirmed)"
                self.logger.info(f"Current balance: {self.web3.from_wei(current_balance, 'ether')} ETH. Waiting...")
                await asyncio.sleep(10)
            except Exception as e:
                self.logger.error(f"Error checking balance: {str(e)}")
                await asyncio.sleep(5)
                
        self.logger.warning(f"Timeout reached after {timeout} seconds. Funds not received.")
        return None

    async def withdraw(self) -> bool:
        """
        Withdraw from exchange to the specified address with retries and log transaction hash.
        Returns True if withdrawal was successful and funds arrived.
        """
        try:
            if not self.config.EXCHANGES.withdrawals:
                raise ValueError("No withdrawal configurations found")
                
            withdrawal_config = self.config.EXCHANGES.withdrawals[0]
            if not withdrawal_config.networks:
                raise ValueError("No networks specified in withdrawal configuration")
                
            # Get chains info
            chains_info = await self.get_chains_info()
            if not chains_info:
                self.logger.error("No available withdrawal networks found")
                return False
                
            currency = withdrawal_config.currency
            exchange_name = self.config.EXCHANGES.name.lower()
            
            # Get available enabled networks
            available_networks = []
            for network in withdrawal_config.networks:
                mapped_network = NETWORK_MAPPINGS[exchange_name].get(network)
                if not mapped_network:
                    continue
                    
                for key, info in chains_info.items():
                    if key == mapped_network and info["withdrawEnabled"]:
                        available_networks.append((network, mapped_network, info))
                        break
                        
            if not available_networks:
                self.logger.error("No enabled withdrawal networks found matching configuration")
                return False
                
            # Randomly select a network
            network, exchange_network, network_info = random.choice(available_networks)
            self.logger.info(f"Selected network for withdrawal: {network} ({exchange_network})")
            
            # Initialize Web3 for the selected network
            rpc_url = CEX_WITHDRAWAL_RPCS.get(network)
            if not rpc_url:
                self.logger.error(f"No RPC URL found for network: {network}")
                return False
            self.network = network
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Set withdrawal amount
            min_amount = max(withdrawal_config.min_amount, network_info["withdrawMin"])
            max_amount = withdrawal_config.max_amount
            
            if min_amount > max_amount:
                self.logger.error(f"Network minimum ({network_info['withdrawMin']}) is higher than configured maximum ({max_amount})")
                return False
                
            amount = round(random.uniform(min_amount, max_amount), random.randint(5, 12))
            
            # Perform the withdrawal
            max_retries = withdrawal_config.retries
            
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Attempting withdrawal {attempt + 1}/{max_retries}")
                    self.logger.info(f"Withdrawing {amount} {currency} to {self.address}")
                    
                    # Get initial balance before withdrawal
                    initial_balance = self.web3.eth.get_balance(self.address)
                    
                    # Get exchange-specific withdrawal parameters
                    params = {
                        'network': exchange_network,
                        'fee': network_info["withdrawFee"],
                        **EXCHANGE_PARAMS[exchange_name]["withdraw"]
                    }
                    
                    # Execute the withdrawal
                    withdrawal = await self.exchange.withdraw(
                        currency,
                        amount,
                        self.address,
                        params=params
                    )
                    
                    self.logger.success(f"Withdrawal initiated successfully: {withdrawal}")
                    
                    # Wait for funds and log transaction hash
                    tx_hash = await self.wait_for_transaction(initial_balance, timeout=withdrawal_config.max_wait_time)
                    if tx_hash:
                        self.logger.success(f"Transaction confirmed with hash: {tx_hash}")
                        await self.exchange.close()
                        return True
                    else:
                        self.logger.warning("Funds not received within timeout, retrying if attempts remain")
                    
                except ccxt.NetworkError as e:
                    if attempt == max_retries - 1:
                        self.logger.error(f"Network error on final attempt: {str(e)}")
                        await self.exchange.close()
                        return False
                    self.logger.warning(f"Network error, retrying: {str(e)}")
                    await asyncio.sleep(5)
                    
                except ccxt.ExchangeError as e:
                    error_msg = str(e).lower()
                    if "insufficient balance" in error_msg:
                        self.logger.error("Insufficient balance in exchange account")
                        await self.exchange.close()
                        return False
                    if "whitelist" in error_msg or "not in withdraw whitelist" in error_msg:
                        self.logger.error(f"Address not in whitelist: {str(e)}")
                        await self.exchange.close()
                        return False
                    if attempt == max_retries - 1:
                        self.logger.error(f"Exchange error on final attempt: {str(e)}")
                        await self.exchange.close()
                        return False
                    self.logger.warning(f"Exchange error, retrying: {str(e)}")
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error during withdrawal: {str(e)}")
                    await self.exchange.close()
                    return False
                    
            self.logger.error(f"Withdrawal failed after {max_retries} attempts")
            await self.exchange.close()
            return False
            
        except Exception as e:
            self.logger.error(f"Fatal error during withdrawal process: {str(e)}")
            await self.exchange.close()
            return False