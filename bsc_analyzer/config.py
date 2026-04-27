"""
BNB Smart Chain Analyzer — Toolkit para análisis on-chain de tokens BEP-20.
Usa MegaNode como proveedor RPC (archive node gratuito).
"""

import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("MEGANODE_RPC_URL", "")
if not RPC_URL:
    raise RuntimeError(
        "MEGANODE_RPC_URL no configurada. Crea un .env con tu API key de MegaNode."
    )

# Conexión singleton
_w3 = None

def get_w3():
    global _w3
    if _w3 is None:
        _w3 = Web3(Web3.HTTPProvider(RPC_URL))
        from web3.middleware import ExtraDataToPOAMiddleware
        _w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return _w3

# Direcciones
TWT_CONTRACT = Web3.to_checksum_address(
    "0x4B0F1812e5Df2A09796481Ff14017e6005508003"
)
WALLET = Web3.to_checksum_address(
    "0xe2fc31F816A9b94326492132018C3aEcC4a93aE1"
)

# Bloques
START_BLOCK = 46080111
TWT_DECIMALS = 18

# ABI para balanceOf y evento Transfer
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]

# Transfer event signature: keccak256("Transfer(address,address,uint256)")
TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Límite de rango de bloques para eth_getLogs en MegaNode
MAX_LOG_RANGE = 49_999

# Paso para muestreo de balance en detección de cambios
SCAN_STEP = 500_000

# Paso para muestreo de tendencia
TREND_STEP = 1_000_000
