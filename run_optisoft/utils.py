from utils.utils import sleep, build_db_path
from utils.models import TxStatusResponse
from curl_cffi.requests.errors import RequestsError
import traceback
from web3.exceptions import TransactionNotFound
from .database.engine import OPDbManager
from .database.models import OPBaseModel
from prettytable import PrettyTable


def pass_transaction(success_message='Transaction passed',
                     forgive_exception=None):
    def outer(func):
        async def wrapper(obj, *args, **kwargs):
            logger = obj.logger.bind(func_name=func.__name__, func_module=func.__module__)
            attempts = 10
            completed = False
            while attempts:
                try:
                    if not completed:
                        tx_hash = await func(obj, *args,  **kwargs)
                        completed = True
                    await sleep(7, 10)
                    receipts = await obj.client.w3.eth.get_transaction_receipt(tx_hash)
                    status = receipts.get("status")
                    if status == 1:
                        logger.success(f'{success_message}. HASH - {obj.explorer}{tx_hash}')
                        await sleep()
                        return TxStatusResponse.GOOD, tx_hash
                    else:
                        logger.error(f'Status {status}. Trying again...')
                        completed = False
                        await sleep(15, 40)
                        attempts -= 1
                except ValueError as e:
                    logger.error(f"{type(e)}: {e}")
                    return TxStatusResponse.INSUFFICIENT_BALANCE, None
                except Exception as e:
                    if forgive_exception and isinstance(e, forgive_exception):
                        return TxStatusResponse.STATUS_ZERO, None
                    message = str(e)
                    if 'Proxy Authentication Required' in message:
                        raise RequestsError('Proxy Authentication Required')
                    elif '' == message:
                        raise RequestsError('Strange error!')
                    elif isinstance(e, TransactionNotFound):
                        logger.info("Transaction not found. Trying again...")
                        await sleep(15, 40)
                        attempts -= 1
                        continue
                    logger.error(f'Error! {type(e)}{e}[{traceback.format_exc()}]. Trying again...')
                    await sleep(15, 40)
                    attempts -= 1
        return wrapper
    return outer

async def show_mon_balance(db_name):
    async with OPDbManager(build_db_path(db_name), OPBaseModel) as db_manager:
        all_data = await db_manager.get_mon_balance()
        table = PrettyTable()
        table.field_names = [
            "Address",
            "Private key",
            'MON balance',
        ]
        for data in all_data:
            table.add_row(
                [
                    data['address'],
                    data['pk'],
                    data['mon_balance']
                ])
        return table