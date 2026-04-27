"""
Rastreo inteligente de transferencias BEP-20.

Estrategia:
  1. Muestrear balanceOf cada SCAN_STEP bloques.
  2. Detectar rangos donde el balance cambió.
  3. Solo en esos rangos, usar eth_getLogs para encontrar las transferencias exactas.
  4. Devolver lista completa de Transfer events decodificados.

Esto evita escanear los ~49M bloques completos.
"""

import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Tuple

from tqdm import tqdm

from .config import (
    get_w3,
    TWT_CONTRACT,
    WALLET,
    START_BLOCK,
    TWT_DECIMALS,
    TRANSFER_SIG,
    MAX_LOG_RANGE,
    SCAN_STEP,
)
from .balance import get_balance_at


@dataclass
class Transfer:
    tx_hash: str
    block_number: int
    sender: str
    receiver: str
    amount: Decimal
    direction: str  # "IN" o "OUT"


def _scan_range_for_transfers(
    from_block: int, to_block: int
) -> List[Transfer]:
    """
    Escanea un rango de bloques con eth_getLogs filtrando por
    eventos Transfer del contrato TWT relativos a la wallet.
    """
    w3 = get_w3()
    wallet_padded = "0x" + WALLET[2:].lower().rjust(64, "0")

    transfers: List[Transfer] = []

    # Función auxiliar para decodificar y añadir transferencias
    def _process_logs(logs, direction: str):
        for log in logs:
            sender = "0x" + log["topics"][1].hex()[-40:]
            receiver = "0x" + log["topics"][2].hex()[-40:]
            raw_amount = int.from_bytes(log["data"], byteorder="big")
            amount = Decimal(raw_amount) / Decimal(10**TWT_DECIMALS)
            transfers.append(Transfer(
                tx_hash="0x" + log["transactionHash"].hex(),
                block_number=log["blockNumber"],
                sender=w3.to_checksum_address(sender),
                receiver=w3.to_checksum_address(receiver),
                amount=amount,
                direction=direction,
            ))

    # Salientes: wallet es el sender (topic1)
    try:
        logs_out = w3.eth.get_logs({
            "address": TWT_CONTRACT,
            "topics": [TRANSFER_SIG, wallet_padded],
            "fromBlock": from_block,
            "toBlock": to_block,
        })
        _process_logs(logs_out, "OUT")
    except Exception:
        pass

    # Entrantes: wallet es el receiver (topic2)
    try:
        logs_in = w3.eth.get_logs({
            "address": TWT_CONTRACT,
            "topics": [TRANSFER_SIG, None, wallet_padded],
            "fromBlock": from_block,
            "toBlock": to_block,
        })
        _process_logs(logs_in, "IN")
    except Exception:
        pass

    return transfers


def find_transfers(
    from_block: int = START_BLOCK,
    to_block: Optional[int] = None,
    progress: bool = True,
) -> List[Transfer]:
    """
    Encuentra todas las transferencias de TWT de la wallet entre dos bloques.

    Usa muestreo de balance para detectar rangos con actividad
    y solo escanea esos rangos con eth_getLogs.
    """
    w3 = get_w3()
    if to_block is None:
        to_block = w3.eth.block_number

    # --- Fase 1: Muestrear balance para detectar rangos con cambios ---
    sample_points = list(range(from_block, to_block + 1, SCAN_STEP))
    if sample_points[-1] < to_block:
        sample_points.append(to_block)

    balances = {}
    desc = "Muestreando balance"
    iterator = tqdm(sample_points, desc=desc) if progress else sample_points
    for blk in iterator:
        balances[blk] = get_balance_at(blk)

    # Detectar rangos donde el balance cambió
    dirty_ranges: List[Tuple[int, int]] = []
    prev_balance = None
    prev_block = from_block
    for blk in sample_points:
        if prev_balance is not None and balances[blk] != prev_balance:
            dirty_ranges.append((prev_block, blk))
        prev_balance = balances[blk]
        prev_block = blk

    if progress:
        print(f"  → {len(dirty_ranges)} rangos con actividad detectados")

    # --- Fase 2: Escanear solo los rangos con cambios ---
    all_transfers: List[Transfer] = []
    for (start, end) in tqdm(dirty_ranges, desc="Escaneando transfers") if progress else dirty_ranges:
        # Partir el rango en chunks de MAX_LOG_RANGE
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + MAX_LOG_RANGE, end)
            transfers = _scan_range_for_transfers(chunk_start, chunk_end)
            # Solo añadir transfers relacionados con la wallet
            for t in transfers:
                if t.sender == WALLET or t.receiver == WALLET:
                    all_transfers.append(t)
            chunk_start = chunk_end

    # Ordenar por bloque
    all_transfers.sort(key=lambda t: t.block_number)
    return all_transfers
