import os

from utils.run_config import ROOT_DIR

CONFIG_PATH = os.path.join(ROOT_DIR, 'config.yaml')
UNICHAIN_BRIDGE_ABI = os.path.join(ROOT_DIR, 'run_optisoft', 'data', 'abis', 'unichain_bridge_abi.json')
UNISWAP_ROUTER_ABI = os.path.join(ROOT_DIR, 'run_optisoft', 'data', 'abis', 'uniswap_router_abi.json')
PERMIT_ABI = os.path.join(ROOT_DIR, 'run_optisoft', 'data', 'abis', 'abi.json')