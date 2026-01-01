from utils.client import Client
from utils.utils import (retry, check_res_status, get_utc_now,
                         get_data_lines, sleep, Logger,
                         read_json, Contract, read_json,
                         approve_asset, asset_balance, get_decimals,
                         generate_random_hex_string, approve_if_insufficient_allowance)
from utils.models import RpcProviders, TxStatusResponse, ChainExplorers
from .config import CONFIG
from .cex_config import Config, get_config 
from .cex_withdraw import CexWithdraw
import random
from .dapps.bridge import UnichainBridge
from .dapps.swap import Uniswap
import traceback
from curl_cffi.requests.errors import RequestsError
from aiohttp.client_exceptions import ClientResponseError


class Task(Logger):
    def __init__(self, session, client: Client, db_manager):
        self.client = client
        self.session = session
        self.db_manager = db_manager
        super().__init__(self.client.address, additional={'pk': self.client.key})
        self.explorer = None

    @property
    async def balance(self):
        return self.client.w3.from_wei(await self.client.w3.eth.get_balance(self.client.address), 'ether')

    async def withdraw_from_okx(self):
        cex_config = get_config()

        cex_withdraw_task = CexWithdraw(
            account_index=0,
            private_key=self.client.key,
            config=cex_config,
            session=self.session,
            client=self.client,
            db_manager=self.db_manager
        )

        try:
            async with cex_withdraw_task:
                success = await cex_withdraw_task.withdraw()
                if success:
                    self.logger.success("Withdrawal from OKX completed successfully!")
                else:
                    self.logger.error("Withdrawal from OKX failed.")
        except Exception as e:
            self.logger.error(f"Error during OKX withdrawal: {str(e)}")
            self.logger.debug(traceback.format_exc())


    async def start_activities(self):
        TASKS_MAP = {
            "swap": Uniswap
        }
        tasks = CONFIG.FLOW.TASKS
        if CONFIG.FLOW.RANDOM:
            random.shuffle(tasks)
        for task in tasks:
            try:
                task_cls = TASKS_MAP[task](session=self.session,
                                           client=self.client,
                                           logger=self.logger,
                                           db_manager=self.db_manager)
                self.logger.info(f"Starting task {task}...")
                await task_cls.run()
            except (RequestsError, ClientResponseError):
                raise
            except Exception as e:
                self.logger.error(f"Error occured in {task} task: {type(e)}: {e}|[{traceback.format_exc()}")
                self.logger.info("Going to next task...")
            sleep_time = random.randint(*CONFIG.SETTINGS.SLEEP_BETWEEN_TASKS)
            self.logger.info(f"Sleeping {sleep_time} seconds before next task...")
            await sleep(sleep_time)
            
    async def unichainbridge(self):
        bridge = UnichainBridge(
            session=self.session,
            client=self.client,
            logger=self.logger,
            db_manager=self.db_manager
        )
        await bridge.run()