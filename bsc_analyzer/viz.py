"""
Visualizaciones con matplotlib.
"""

from decimal import Decimal
from typing import List, Tuple

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


def plot_balance_trend(
    data: List[Tuple[int, Decimal]],
    title: str = "TWT Balance Trend",
    save_path: str = None,
):
    """Gráfico de línea: saldo TWT vs número de bloque."""
    blocks, balances = zip(*data)
    balances_float = [float(b) for b in balances]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(blocks, balances_float, color="#F0B90B", linewidth=2, marker="o", markersize=3)
    ax.fill_between(blocks, balances_float, alpha=0.1, color="#F0B90B")

    ax.set_xlabel("Block Number")
    ax.set_ylabel("TWT Balance")
    ax.set_title(title)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_top_counterparties(
    data: List[Tuple[str, Decimal, int]],
    title: str = "Top Counterparties (Outgoing TWT)",
    save_path: str = None,
):
    """Gráfico de barras horizontales: top destinatarios de transfers salientes."""
    if not data:
        print("No outgoing transfers to display.")
        return

    addresses, amounts, counts = zip(*data)
    labels = [f"{a[:6]}...{a[-4:]}" for a in addresses]
    amounts_float = [float(a) for a in amounts]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = plt.cm.Oranges_r([0.3 + 0.7 * i / len(labels) for i in range(len(labels))])

    bars = ax.barh(labels, amounts_float, color=colors, edgecolor="#333", linewidth=0.5)
    ax.set_xlabel("Total TWT Sent")
    ax.set_title(title)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.invert_yaxis()

    for bar, amt, cnt in zip(bars, amounts_float, counts):
        ax.text(bar.get_width() + max(amounts_float) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{amt:,.2f} TWT ({cnt} tx)",
                va="center", fontsize=9)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()
