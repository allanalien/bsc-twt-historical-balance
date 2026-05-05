# Support Specialist Manual — Blockchain Query Systems

## Who this manual is for

You're a Support Specialist for a blockchain data query tool. This manual will teach you everything you need to understand the technology stack, troubleshoot issues, and explain concepts to users — even if you're starting from zero blockchain knowledge.

---

## Part 1: Blockchain Fundamentals

### What is a blockchain?

A blockchain is a **distributed ledger** — a database shared across thousands of computers (nodes) that all agree on the same history. Think of it as a Google Sheet that everyone can see, nobody can delete from, and new rows can only be added if the network agrees.

**Key concepts:**

| Term | Simple explanation |
|---|---|
| **Block** | A batch of transactions, like a page in a ledger |
| **Block number** | The position of that block in the chain (1, 2, 3... millions) |
| **Transaction (tx)** | One action recorded on-chain (send tokens, call a contract, etc.) |
| **Block hash** | A unique fingerprint of a block's contents |
| **State** | The "current snapshot" of all account balances and contract data at a given block |

### Why "historical" queries are special

A normal node only keeps the **latest state** (current balances). An **archive node** keeps the state for **every block in history**. Querying "what was the balance at block 46,080,111?" requires an archive node, because that was ~49 million blocks ago.

Analogy: A full node is like having only today's bank statement. An archive node is like having every bank statement ever issued.

### What is BNB Smart Chain (BSC)?

BSC is an EVM-compatible blockchain (explained below) created by Binance. Key traits:

- **Block time:** ~3 seconds (very fast)
- **Consensus:** Proof of Staked Authority (PoSA) — a variant of Proof of Authority
- **Native token:** BNB
- **Token standard:** BEP-20 (identical to Ethereum's ERC-20)
- **Node count:** 21 validators (more centralized than Ethereum, much faster)

### What does "EVM-compatible" mean?

EVM = Ethereum Virtual Machine. It's the "computer" that runs smart contracts. Any chain that's EVM-compatible (BSC, Polygon, Arbitrum, Avalanche) can run the same contract code. That means:

- Same token standards (ERC-20 = BEP-20)
- Same JSON-RPC API (the protocol for talking to nodes)
- Same address format (0x...)
- Same tooling (web3.py, ethers.js, MetaMask)

---

## Part 2: JSON-RPC — How we talk to the blockchain

### What is JSON-RPC?

It's a protocol. Your script sends a JSON object to a node URL, the node processes it, and returns a JSON response. No different from calling a REST API — just a different format.

**Request example (eth_call):**
```json
{
  "jsonrpc": "2.0",
  "method": "eth_call",
  "params": [
    {
      "to": "0x4B0F1812e5Df2A09796481Ff14017e6005508003",
      "data": "0x70a08231000000000000000000000000e2fc31f816a9b94326492132018c3aecc4a93ae1"
    },
    "0x2BF206F"
  ],
  "id": 1
}
```

**Response (the balance in wei):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": "0x00000000000000000000000000000000000000000000a3c9f3a1b4e2d3c5e70000"
}
```

### Key RPC methods we use

| Method | What it does | Parameters |
|---|---|---|
| `eth_call` | Execute a contract function (read-only) at a specific block | `{to, data}`, `block_number` |
| `eth_getLogs` | Search for event logs emitted by a contract | `{address, topics, fromBlock, toBlock}` |
| `eth_blockNumber` | Get the current block number | None |
| `eth_chainId` | Get the chain ID (56 = BSC) | None |

### eth_call vs calling balanceOf directly

If you call a node's `eth_call` **without** a block number, you get the **current** balance. Add `block_identifier: 46080111` and the node replays the function using the state from that exact block — giving you the **historical** balance. Same function, different point in time.

### eth_getLogs and events

When tokens are transferred, the contract emits a `Transfer` event. These events are stored as "logs" on-chain. `eth_getLogs` lets us search for specific events within a block range.

The `Transfer` event signature is the keccak256 hash of `"Transfer(address,address,uint256)"`. By filtering on this hash, we find all token transfers.

**Filtering by wallet:**
- Topic 1 = sender (indexed)
- Topic 2 = receiver (indexed)
- To find all outgoing transfers: filter topic1 = wallet address
- To find all incoming transfers: filter topic2 = wallet address

---

## Part 3: Tokens, addresses, and encoding

### BEP-20 / ERC-20 tokens

A token contract on BSC is just a smart contract that follows the BEP-20 standard. Every BEP-20 contract implements these functions:

- `balanceOf(address)` → returns how many tokens an address holds
- `transfer(to, amount)` → sends tokens
- `Transfer(from, to, amount)` → event emitted on every transfer

The TWT token contract is at `0x4B0F1812e5Df2A09796481Ff14017e6005508003` on BSC.

### Decimals (wei conversion)

Tokens have decimals. TWT has 18 decimals, meaning:
- **1 TWT** = **1,000,000,000,000,000,000** units (1 × 10^18)
- The blockchain stores everything in the smallest unit (like cents vs dollars)
- To display: divide raw value by `10^decimals`
- To encode: multiply human value by `10^decimals`

**Example:** If `balanceOf()` returns `772344589576781554442724`, dividing by `10^18` gives `772,344.589576781554442724 TWT`.

### Address formatting (EIP-55)

Ethereum addresses have a checksum — some letters are uppercase, some lowercase. This helps detect typos. Example:

```
Lowercase:  0x4b0f1812e5df2a09796481ff14017e6005508003
Checksum:   0x4B0F1812e5Df2A09796481Ff14017e6005508003
```

web3.py 7.x **validates** checksums. If an address has the wrong case pattern, it rejects it with `InvalidAddress`. Always use `Web3.to_checksum_address()` to normalize.

### Topic encoding for events

Indexed event parameters are stored as "topics" — 32-byte (64 hex character) values. Addresses must be left-padded with zeros:

```
Address:      0xe2fc31F816A9b94326492132018C3aEcC4a93aE1
As topic:     0x000000000000000000000000e2fc31f816a9b94326492132018c3aecc4a93ae1
```

### Block numbers in hex

JSON-RPC accepts block numbers in decimal or hex. Our code uses decimal integers and web3.py converts them. For reference:

```
Block 46080111 → 0x2BF206F (hex)
Block 50000     → 0xC350    (hex)
```

---

## Part 4: How our system works (internals)

### The smart transfer tracking algorithm

This is the most important piece. Scanning 49 million blocks directly is impossible with rate limits. Here's the two-phase approach:

```
Phase 1: Balance sampling (eth_call)
┌─────────────────────────────────────────────────┐
│ Block 46.0M: 772K TWT                            │
│ Block 46.5M: 772K TWT  ← No change, skip!       │
│ Block 47.0M: 796K TWT  ← CHANGED! Mark dirty    │
│ Block 47.5M: 422K TWT  ← CHANGED! Mark dirty    │
│ ...                                              │
└─────────────────────────────────────────────────┘

Phase 2: Event scanning (eth_getLogs)
Only scan dirty ranges:
┌─────────────────────────────────────────────────┐
│ Range 46.5M → 47.0M: scan in 49,999-block chunks│
│ Range 47.0M → 47.5M: scan in 49,999-block chunks│
│ ...                                              │
└─────────────────────────────────────────────────┘
```

This reduces ~1,000 RPC calls to ~200-300 for the full analysis.

### Why POA middleware is needed

BSC is Proof of Authority. POA blocks have an `extraData` field > 32 bytes. web3.py expects ≤ 32 bytes for Proof of Work chains and throws `ExtraDataLengthError`. The middleware `ExtraDataToPOAMiddleware` tells web3.py to accept longer extraData.

This is a **required** step for BSC. If you forget it, every `eth_getBlock` or `eth_call` that returns block data will fail.

### Rate limits and chunking

NodeReal's free tier allows:
- `eth_getLogs` max range: **49,999 blocks** per request
- General rate limit: ~25 requests/second (generous)

Our code handles this by splitting every dirty range into ≤49,999 block chunks before making `eth_getLogs` calls.

---

## Part 5: Troubleshooting Guide

### Error: `missing trie node` or `historical state not available`

**What it means:** The node doesn't have the state data for the requested historical block.

**Why:** You're connected to a non-archive node (public RPC, light node, etc.).

**Fix:**
1. Verify you're using NodeReal (`https://bsc-mainnet.nodereal.io/v1/...`)
2. Check the API key is valid (not expired, not rate-limited)
3. Try querying a very recent block first to verify connectivity

### Error: `exceed maximum block range: 50000`

**What it means:** An `eth_getLogs` request asked for more than 49,999 blocks.

**Why:** The code isn't chunking the range properly, or the dirty range is huge.

**Fix:**
1. Check `MAX_LOG_RANGE = 49_999` in `config.py`
2. Verify the chunking loop in `transfers.py` is working
3. Try reducing `SCAN_STEP` to produce smaller dirty ranges

### Error: `InvalidAddress: EIP-55 checksum`

**What it means:** An address has incorrect mixed-case formatting.

**Why:** The address was typed manually with wrong case, or copied from a source that doesn't use EIP-55.

**Fix:** Run `Web3.to_checksum_address("0xyouraddress")` to get the correct checksum.

### Error: `ExtraDataLengthError`

**What it means:** web3.py received a block with POA-style extraData and rejected it.

**Fix:** Ensure `ExtraDataToPOAMiddleware` is injected. Check `config.py` has:
```python
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
```

### Issue: Script can't connect (timeout)

**Causes:**
- API key is invalid or expired
- Network issues
- NodeReal is down (rare, check status)

**Debug steps:**
1. Test the URL in a browser: `https://bsc-mainnet.nodereal.io/v1/YOUR-KEY`
2. Try with `curl`:
   ```bash
   curl -X POST https://bsc-mainnet.nodereal.io/v1/YOUR-KEY \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```
3. Check the `.env` file exists and has the correct format

### Issue: Transfers found = 0 even though balance changed

**Possible causes:**
- The token contract uses a non-standard event signature
- The balance change came from a mint/burn (no Transfer event to this wallet)
- The wallet received tokens via an internal mechanism (staking rewards, airdrop contract)

**Debug:** Run a raw `eth_getLogs` with no wallet filter on a small range to see all Transfer events for the token contract.

---

## Part 6: Tools and references

### Essential tools

| Tool | Purpose | URL |
|---|---|---|
| NodeReal | Free archive RPC for BSC | nodereal.io |
| BscScan | Block explorer (view txns) | bscscan.com |
| web3.py docs | API reference | web3py.readthedocs.io |
| eth_abi | ABI encoding reference | eth-abi.readthedocs.io |

### Useful code snippets for debugging

**Check if a node is archive:**
```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("YOUR_RPC"))
# Try querying 1M blocks ago
old_block = w3.eth.block_number - 1_000_000
try:
    w3.eth.get_balance("0x0000000000000000000000000000000000000000", block_identifier=old_block)
    print("Archive node: YES")
except:
    print("Archive node: NO")
```

**Get block info:**
```python
block = w3.eth.get_block(46080111)
print(block.timestamp)  # Unix timestamp
print(block.number)     # Block number
```

**List all Transfer events for any token (raw):**
```python
logs = w3.eth.get_logs({
    "address": TOKEN_ADDRESS,
    "topics": ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"],
    "fromBlock": START,
    "toBlock": START + 1000,  # Keep it small
})
for log in logs:
    print(f"Block {log.blockNumber}: tx {log.transactionHash.hex()}")
```

---

## Part 7: Glossary

| Term | Definition |
|---|---|
| **ABI** | Application Binary Interface — the "API spec" of a smart contract |
| **Archive node** | A node that stores all historical state, not just the latest |
| **BEP-20** | Token standard on BSC (identical to ERC-20) |
| **Block** | A batch of transactions confirmed by the network |
| **eth_call** | Execute a contract function read-only at a specific block |
| **eth_getLogs** | Query for event logs emitted by contracts |
| **EVM** | Ethereum Virtual Machine — the runtime for smart contracts |
| **JSON-RPC** | The protocol for communicating with blockchain nodes |
| **keccak256** | The hash function used by Ethereum/BSC |
| **POA** | Proof of Authority — BSC's consensus mechanism |
| **RPC** | Remote Procedure Call — the node's API endpoint |
| **State** | The snapshot of all balances/contract data at a given block |
| **Topic** | An indexed event parameter, used for filtering in eth_getLogs |
| **Wei** | The smallest unit of a token (1 TWT = 10^18 wei) |
