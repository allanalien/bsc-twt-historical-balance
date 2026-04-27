"""
Análisis de contrapartes y reportes.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Tuple

from .transfers import Transfer


def top_counterparties(
    transfers: List[Transfer],
    top_n: int = 5,
) -> List[Tuple[str, Decimal, int]]:
    """
    Agrupa transferencias salientes por destinatario.
    Retorna top N: (direccion, monto_total_twt, num_transferencias).
    """
    outgoing: Dict[str, Decimal] = defaultdict(Decimal)
    counts: Dict[str, int] = defaultdict(int)

    for t in transfers:
        if t.direction == "OUT":
            outgoing[t.receiver] += t.amount
            counts[t.receiver] += 1

    sorted_items = sorted(outgoing.items(), key=lambda x: x[1], reverse=True)
    return [(addr, amt, counts[addr]) for addr, amt in sorted_items[:top_n]]


def transfer_summary(transfers: List[Transfer]) -> dict:
    """Resumen agregado de transferencias."""
    total_in = sum(t.amount for t in transfers if t.direction == "IN")
    total_out = sum(t.amount for t in transfers if t.direction == "OUT")
    num_in = sum(1 for t in transfers if t.direction == "IN")
    num_out = sum(1 for t in transfers if t.direction == "OUT")

    unique_counterparties = set()
    for t in transfers:
        if t.direction == "IN":
            unique_counterparties.add(t.sender)
        else:
            unique_counterparties.add(t.receiver)

    return {
        "total_txs": len(transfers),
        "incoming_count": num_in,
        "outgoing_count": num_out,
        "total_in_twt": total_in,
        "total_out_twt": total_out,
        "net_flow_twt": total_in - total_out,
        "unique_counterparties": len(unique_counterparties),
    }
