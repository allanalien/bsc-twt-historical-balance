"""
Consultas de balance histórico vía eth_call.
"""

from decimal import Decimal
from .config import get_w3, TWT_CONTRACT, WALLET, TWT_DECIMALS, ERC20_ABI


def get_balance_at(block_number: int) -> Decimal:
    """
    Devuelve el balance de TWT de la wallet en un bloque específico.
    Usa eth_call con block_identifier para consulta histórica.
    """
    w3 = get_w3()
    contract = w3.eth.contract(address=TWT_CONTRACT, abi=ERC20_ABI)
    data = contract.encode_abi("balanceOf", args=[WALLET])

    raw = w3.eth.call(
        {"to": TWT_CONTRACT, "data": data},
        block_identifier=block_number,
    )
    balance_wei = int.from_bytes(raw, byteorder="big")
    return Decimal(balance_wei) / Decimal(10**TWT_DECIMALS)
