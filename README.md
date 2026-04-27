# BSC Historical Token Balance Analyzer

On-chain auditing toolkit for BEP-20 tokens on BNB Smart Chain. Query historical balances, track transfers, and generate analytics — directly from the blockchain, no third-party APIs like BscScan needed.

## Requirements

- Python 3.8+
- Free API key from [NodeReal](https://www.nodereal.io/) (archive node access)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file with your NodeReal RPC URL:

```
MEGANODE_RPC_URL=https://bsc-mainnet.nodereal.io/v1/your-api-key
```

## Usage

### Quick balance check (CLI)

Query a token balance at an exact block:

```bash
python3 check_twt_balance.py
```

Defaults to TWT token, wallet `0xe2fc31...`, block `46080111`. Edit the constants at the top of the script to change token/wallet/block.

### Full analysis (Jupyter Notebook)

```bash
jupyter notebook notebooks/twt_analysis.ipynb
```

Run each cell with `Shift+Enter`. The notebook includes:

| Section | Description |
|---|---|
| Setup | Connect to BSC via NodeReal |
| Historical balance | Token balance at any past block |
| Trend | Balance evolution chart (every 1M blocks) |
| Transfers | BEP-20 transfer tracking with smart change detection |
| Top counterparties | Ranking of outgoing transfer destinations |
| Ad-hoc query | Balance at any arbitrary block |

## How it works

### Historical balance (`eth_call`)

Executes `balanceOf(wallet)` against the blockchain state frozen at a specific block. Returns the balance as it was at that exact moment, not the current one.

### Transfer tracking

Instead of scanning all blocks with `eth_getLogs`, the algorithm:

1. Samples `balanceOf` every 500K blocks
2. Detects only ranges where the balance changed
3. Scans only those ranges with `eth_getLogs` (in 49,999 block chunks)

This reduces ~2,000 RPC calls to ~200 for a typical 50M block range.

### Analytics

- **Trend**: samples balance every 1M blocks and plots it
- **Counterparties**: groups outgoing transfers by recipient, shows top N

## Using with other tokens or wallets

Edit `bsc_analyzer/config.py`:

```python
TWT_CONTRACT = Web3.to_checksum_address("0xNewToken...")
WALLET = Web3.to_checksum_address("0xNewWallet...")
START_BLOCK = 12345678   # Block to start analysis from
```

## Compatibility

Works with any EVM chain (Ethereum, Polygon, Arbitrum, etc.). Just change `MEGANODE_RPC_URL` to an archive node RPC for your target network.

## Project structure

```
bsc_analyzer/
├── config.py       # Constants, RPC connection
├── balance.py      # eth_call for historical balance
├── transfers.py    # Smart BEP-20 transfer tracking
├── trend.py        # Balance trend sampling
├── reports.py      # Counterparty analysis & summaries
└── viz.py          # Matplotlib charts
check_twt_balance.py  # CLI script
notebooks/
└── twt_analysis.ipynb  # Interactive notebook
```

## Limitations

- Transfer tracking takes ~1 min per million blocks with activity
- NodeReal has rate limits; for large scans, consider smaller batch sizes
