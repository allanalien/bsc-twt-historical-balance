"""
Muestreo de tendencia de balance a intervalos regulares.
"""

from decimal import Decimal
from typing import List, Tuple

from tqdm import tqdm

from .config import get_w3, START_BLOCK, TREND_STEP
from .balance import get_balance_at


def sample_balance_trend(
    from_block: int = START_BLOCK,
    to_block: int = None,
    step: int = TREND_STEP,
    progress: bool = True,
) -> List[Tuple[int, Decimal]]:
    """
    Muestrea el balance cada `step` bloques.
    Retorna lista de (bloque, balance_twt).
    """
    w3 = get_w3()
    if to_block is None:
        to_block = w3.eth.block_number

    points = list(range(from_block, to_block + 1, step))
    if points[-1] < to_block:
        points.append(to_block)

    results = []
    iterator = tqdm(points, desc="Muestreando tendencia") if progress else points
    for blk in iterator:
        results.append((blk, get_balance_at(blk)))

    return results
