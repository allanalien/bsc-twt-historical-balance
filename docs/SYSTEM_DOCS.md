# BSC Historical Token Balance Analyzer — System Documentation

## Overview

A Python toolkit for querying **historical** BEP-20 token balances and tracking token transfers on BNB Smart Chain (BSC). It operates directly against the blockchain via JSON-RPC — no third-party indexers or APIs like BscScan are required.

## Architecture

```
User (CLI or Jupyter Notebook)
        │
        ▼
   bsc_analyzer/  (Python package)
        │
        ▼
   web3.py  (JSON-RPC over HTTPS)
        │
        ▼
   NodeReal Archive Node  (BSC Mainnet)
```

The system has two entry points:

| Entry point | File | Purpose |
|---|---|---|
| CLI script | `check_twt_balance.py` | Single balance query at a specific block |
| Jupyter notebook | `notebooks/twt_analysis.ipynb` | Full interactive analysis (trend, transfers, counterparties) |

## Core modules

### `config.py` — Connection & constants

- Loads the `MEGANODE_RPC_URL` from `.env`
- Creates a singleton Web3 connection (reused across modules)
- Injects `ExtraDataToPOAMiddleware` (BSC is a Proof-of-Authority chain and requires this)
- Defines constants: token contract, wallet, block numbers, event signatures

### `balance.py` — Historical balance query

```
get_balance_at(block_number: int) -> Decimal
```

Uses `eth_call` with `block_identifier` to execute `balanceOf(address)` against the EVM state **as it existed at that block**. This is the key difference from a "current" balance query: the node replays the contract code using the historical state trie for that block number.

**RPC call:** `eth_call`
**Parameters:** `{to: contract, data: encoded_abi}`, `block_identifier: 46080111`

### `transfers.py` — Smart BEP-20 transfer tracking

```
find_transfers(from_block, to_block) -> List[Transfer]
```

**Problem:** Scanning all blocks with `eth_getLogs` is too slow (49M blocks / 50K per request = ~1,000 requests).

**Solution — two-phase algorithm:**

1. **Sampling phase:** Call `get_balance_at()` every 500,000 blocks. Identify ranges where the balance changed between consecutive samples.
2. **Scanning phase:** Only scan those "dirty" ranges with `eth_getLogs`, filtering for `Transfer(address,address,uint256)` events where the wallet is either the sender (topic1) or receiver (topic2).

**RPC calls:** `eth_call` (phase 1) + `eth_getLogs` (phase 2)

**Data decoded per transfer:**
- `tx_hash` — transaction hash
- `block_number` — block where the transfer occurred
- `sender` / `receiver` — addresses involved
- `amount` — TWT amount (already converted from wei)
- `direction` — "IN" or "OUT"

### `trend.py` — Balance trend sampling

```
sample_balance_trend(from_block, to_block, step=1_000_000) -> List[(block, balance)]
```

Samples `get_balance_at()` at regular intervals and returns a time series. Lightweight (~50 RPC calls for the full range).

### `reports.py` — Analytics

- `transfer_summary()` — aggregates: total txs, incoming/outgoing counts, total volume, net flow, unique counterparties
- `top_counterparties()` — groups outgoing transfers by recipient address, returns top N sorted by total TWT sent

### `viz.py` — Visualization

- `plot_balance_trend()` — line chart with block numbers on x-axis, TWT balance on y-axis
- `plot_top_counterparties()` — horizontal bar chart of top destinations

## Key technical details

### Why an archive node is required

A "full node" only keeps recent state. An "archive node" stores the full state trie for every block in history. When you call `eth_call` with a `block_identifier` from months ago, only an archive node can replay that state.

Public RPCs (Binance dataseed, publicnode.com) are **not** archive nodes — they respond with `missing trie node` or `historical state not available` for past blocks.

**NodeReal's free plan includes archive access**, which is why this project uses it.

### Block range limit

NodeReal enforces a maximum `eth_getLogs` block range of **49,999 blocks**. Attempting 50,000+ returns:
```
exceed maximum block range: 50000
```
The code handles this by chunking all dirty ranges into ≤49,999 block segments.

### POA middleware

BSC uses Proof of Authority (not Proof of Work). Blocks have `extraData` fields larger than 32 bytes, which causes web3.py to throw `ExtraDataLengthError`. The middleware `ExtraDataToPOAMiddleware` suppresses this validation.

### EIP-55 address checksums

web3.py 7.x+ validates Ethereum addresses against EIP-55 (mixed-case checksum). All addresses in `config.py` are run through `Web3.to_checksum_address()` to ensure valid format.

### Topic encoding for eth_getLogs

ERC-20/BEP-20 `Transfer` event signature:
```
keccak256("Transfer(address,address,uint256)")
→ 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
```

For filtering, indexed parameters (topics) must be 32-byte left-padded:
```
Address 0xe2fc31...
→ Topic 0x000000000000000000000000e2fc31f816a9b94326492132018c3aecc4a93ae1
```

## Configuration reference

Edit `bsc_analyzer/config.py` to change:

| Variable | Purpose | Example |
|---|---|---|
| `TWT_CONTRACT` | Token contract address | `0x4B0F1812e5DF...` |
| `WALLET` | Target wallet address | `0xe2fc31F816A9...` |
| `START_BLOCK` | Analysis start block | `46080111` |
| `TWT_DECIMALS` | Token decimals | `18` |
| `SCAN_STEP` | Balance sampling interval | `500000` |
| `TREND_STEP` | Trend sampling interval | `1000000` |

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| web3.py | 7.7.0 | Ethereum/BSC JSON-RPC client |
| python-dotenv | 1.1.0 | Load `.env` configuration |
| matplotlib | 3.5+ | Chart generation |
| pandas | 1.3+ | Tabular data display |
| tqdm | 4.60+ | Progress bars |
| jupyter | 1.0+ | Notebook interface |

## Common issues

| Error | Cause | Solution |
|---|---|---|
| `missing trie node` | RPC node is not an archive node | Use NodeReal or another archive provider |
| `exceed maximum block range: 50000` | `eth_getLogs` range too large | Chunk into ≤49,999 block segments |
| `InvalidAddress: EIP-55 checksum` | Address has incorrect mixed-case | Use `Web3.to_checksum_address()` |
| `ExtraDataLengthError` | BSC is POA, needs middleware | Inject `ExtraDataToPOAMiddleware` |
| `MEGANODE_RPC_URL not configured` | No `.env` file or env var | Create `.env` with your NodeReal key |
