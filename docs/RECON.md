# rwaUSD Oracle Recon — what we know before talking to Multipli

Sources: public docs + Etherscan + live `eth_call` against Ethereum mainnet.
On-chain values below were read at **block 26009331, 2026-09-19 05:00 UTC**. Re-read before
quoting — `zzz`, `read()` and the feed age move constantly.

## TL;DR

The deployed rwaUSD core on Ethereum is a **MakerDAO DSS fork** (Vat, Spotter, Jug, Vow, Dog,
Cure, End, GemJoin, Clipper, DssCdpManager...). The oracle path for PAXG collateral is:

```
Chainlink aggregator (XAU/PAXG feed)
        |  latestRoundData(), decimals()
        v
PriceFeedAdapter        0x82F5790Bd1c96790E4c3a3ebC8142bD4D6F8b1CD   <- custom, Ownable
        |  peek() -> (bytes32 val, bool has)      [DSValue interface]
        v
OSM                     0x89fbAe0302b8790D55fa36E6Ab09ac93F865993a   <- stock Maker osm.sol
        |  peek() = current, peep() = queued next
        v
Spotter                 0xf3aee748355bb07CBe702B4ff8dBE6118b34e2A2
        |  applies mat (liquidation ratio) -> spot
        v
Vat                     0xbC22e8C15bC476EF4FD0124c5A03b23607e30D2C
        |
        v
Dog 0x15a3... -> Clipper 0x62B7... (liquidation auctions)
```

## Verified facts

**OSM** (`0x89fbAe03...`) — source verified, contract name `OSM`, solc 0.6.12, optimizer 8000 runs.
Header reads `Copyright (C) 2018-2020 Maker Ecosystem Growth Holdings, INC.` — it is **unmodified
upstream `osm.sol`**. Functions: `rely/deny` (wards auth), `kiss/diss` (bud read-whitelist),
`poke`, `peek`, `peep`, `read`, `stop/start`, `void`, `change(src)`, `step(hop)`, `zzz`, `pass`.

- Deployed 168 days ago by `0xEEfa1a4bE1251d14CA84825CB0Be8D55f2A8251f` (EOA, now has `wards == 0`).
- **LIVE AND ACTIVELY POKED, hourly.** Verified on-chain 2026-09-19 05:00 UTC:
  `hop() = 3600` (1h), `zzz() = 1789790400` (2026-09-19 04:00 UTC, ~1h old),
  `stopped() = 0`, `pass() = true`, `src()` == the PriceFeedAdapter.
- Etherscan's *top-level* tx list stops ~130 days ago (121 txs, all `Poke`, from EOA
  `0xcCdA4D0e…`). Pokes clearly continue by another route — almost certainly internal
  transactions from a keeper/Safe — so top-level tx history is NOT a liveness signal here.
- `peek()` / `peep()` revert `OSM/contract-not-whitelisted` for outsiders. `bud` whitelist is
  Spotter = 1, PAXG Clipper = 1. Correct Maker wiring. To read them, impersonate Spotter on a fork.

**PriceFeedAdapter** (`0x82F5790B...`) — source verified, contract name `PriceFeedAdapter`,
custom (not Maker), solc 0.6.12. `src/adapter.sol`.

- Constructor takes `(asset_, feed_)`. Wraps a Chainlink `AggregatorV3`-shaped `IPriceFeed`
  (`latestRoundData()`, `decimals()`) and re-exposes it as Maker's DSValue `peek()`/`read()`.
  So its entire job is: staleness check + decimal normalization + interface translation.
- **Ownable, not ward-based**: `transferOwnership`, `setAsset`, `setPriceFeed`, `setMaxDelay`,
  `pause`, `unpause`. No timelock.
- Verified live: `owner()` = `0x194eBc1B9B382ef0E6998cAAcE59aF843cf53b99` (the "RWAUSD Operator
  wallet" in the docs) = a **Gnosis Safe v1.4.1, threshold 4 of 8 owners** (6 EOAs, 2 contracts).
  Multisig, not an EOA — but also **not a timelock**.
- `asset()` = `0x45804880De22913dAFE09f4980848ECE6EcbAf78` (PAXG).
- `priceFeed()` = `0x9944d86cEB9160aF5C5feB251FD671923323f8C3` = Chainlink **PAXG / USD**,
  8 decimals, aggregator `0x6795d4a47c9c8f4117b409d966259cdcf6a9eb6e`.
- `maxDelay()` = **86400 s (24 h)** — the only freshness guard. Owner-settable, unbounded, no delay.
- `paused()` = false. `read()` = 4372.478143390 USD (wad).
- `setPriceFeed(newFeed)` swaps the entire upstream data source in one Safe transaction.

## Doc-vs-deployment gap (important)

The docs describe **two different architectures**:

1. **Deployed today** — the Maker DSS fork above. OSM + PriceFeedAdapter. This is what the problem
   statement means by "OSM and adapter contracts, which currently perform the oracle role."
2. **Documented in `/technical-architecture/`** — a newer design: `PriceRouter`
   (`getPrice(profileId) -> (price, status, updatedAt)`), `SignedFeedVerifier` (EIP-712 signed
   messages, N-of-M quorum, validity window), `PriceGuards`, `RiskRegistry`, `AssetAdapter`,
   `UnwindEngine`, `AuctionHouse`, `PegRail`. Status enum: `OK / STALE / DISPUTED / HALTED`.

**Ask which one we're targeting.** They are not the same problem.

Also note: docs say tokenized gold uses "Spot XAU/USD primary feed with market TWAP sanity checks,"
but the deployed adapter ABI has no TWAP check — only `maxDelay`. Either the sanity check lives
upstream in Chainlink, or that sentence describes the v2 design. Worth asking.

## Documented governance (from docs, unverified on-chain)

- **Timelock Governor** — RiskRegistry / FeeAccumulator / PegRail params, onboards profiles.
- **Guardian** — can pause risk-increasing ops, cannot relax params.
- **Oracle Admin** — signer sets and feed config, "ideally via timelock" (their word, "ideally").
- Minimum delay on parameter changes: **24h**. Emergency pause: **immediate**.
- Emergency wind-down can "optionally lock prices at the last verified levels."

**Verified: one 4-of-8 Safe holds all three.** `0x194eBc1B…` is simultaneously the
PriceFeedAdapter `owner()`, an OSM `ward`, and a Spotter `ward`. No timelock anywhere on the
oracle path. The docs' 24h parameter-change delay and "Oracle Admin ideally via timelock" do not
appear to be enforced on these deployed contracts — confirm whether that's by design.

## Measured staleness budget

```
Chainlink PAXG/USD round age accepted by adapter : up to 86400 s  (24 h)   <- maxDelay
OSM delay before a fetched value becomes current : up to  3600 s  ( 1 h)   <- hop
------------------------------------------------------------------------
worst-case age of the price the Vat liquidates on:      ~90000 s  (~25 h)
```

Observed at 2026-09-19 05:00 UTC: the upstream Chainlink round was **12.5 h old**
(`updatedAt` = 2026-09-18 16:30 UTC) and was being accepted normally.

Note `maxDelay` (24 h) is set equal to the Chainlink PAXG/USD heartbeat, so there is zero
margin: one missed heartbeat trips the adapter. That is a deliberate-looking choice with a
liveness/safety trade on both sides — worth asking about, and worth measuring.

## Run this yourself (needs an RPC URL)

```bash
export ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
OSM=0x89fbAe0302b8790D55fa36E6Ab09ac93F865993a
ADP=0x82F5790Bd1c96790E4c3a3ebC8142bD4D6F8b1CD
SPOT=0xf3aee748355bb07CBe702B4ff8dBE6118b34e2A2

cast call $OSM "hop()(uint16)"        # delay window in seconds
cast call $OSM "zzz()(uint64)"        # timestamp of last poke
cast call $OSM "stopped()(uint256)"   # 1 = frozen
cast call $OSM "src()(address)"       # should equal $ADP
cast call $OSM "wards(address)(uint256)" 0xEEfa1a4bE1251d14CA84825CB0Be8D55f2A8251f

cast call $ADP "owner()(address)"     # EOA, multisig, or timelock?
cast call $ADP "maxDelay()(uint256)"
cast call $ADP "priceFeed()(address)" # the actual Chainlink aggregator
cast call $ADP "paused()(bool)"
cast call $ADP "read()(bytes32)"

# peek/read are bud-gated; impersonate a whitelisted reader on a fork:
anvil --fork-url $ETH_RPC_URL
```

Then fork and replay. `anvil --fork-url` gives us the real system to instrument in Phase 3 —
we do NOT need a testnet deployment from them.

## Sharper questions for the mentors

Skip the "what is an OSM" walkthrough. Ask these:

1. Is the target the deployed DSS fork, or the PriceRouter/SignedFeedVerifier design in the docs?
2. What actually calls `OSM.poke()` and `Spotter.poke()` now? Top-level txs stopped ~130 days
   ago but `zzz` is current, so it's routed through something. What's the keeper, its funding,
   its monitoring, and its failover?
3. Why is `maxDelay` exactly equal to the feed heartbeat (both 24 h)? And is a ~25 h worst-case
   price age acceptable for gold collateral under the current liquidation parameters?
4. No timelock sits in front of `setPriceFeed` / `setMaxDelay` / OSM `change()` — a 4-of-8 Safe
   can swap the data source atomically. Intentional? What compensating controls exist?
5. PAXG is the only collateral with a published OSM+adapter. What prices the tokenized
   equities, treasuries, and the other 100+ assets today?
6. Which of the 100+ assets are actually live as collateral today, and on which chains?

## Sources

- https://docs.multipli.fi/llms.txt (full docs index)
- https://docs.multipli.fi/technical-architecture/rwausd-contract-addresses.md
- https://docs.multipli.fi/technical-architecture/contract-suite.md
- https://docs.multipli.fi/technical-architecture/collateral-and-oracle-profile.md
- https://docs.multipli.fi/technical-architecture/governance-and-emergency-controls.md
- https://docs.multipli.fi/technical-architecture/functions-and-events.md
- https://docs.multipli.fi/technical-architecture/unwind-and-peg-module.md
- https://docs.multipli.fi/technical-architecture/for-integrators.md
- https://docs.multipli.fi/risks/audit-reports.md
- https://etherscan.io/address/0x89fbAe0302b8790D55fa36E6Ab09ac93F865993a
- https://etherscan.io/address/0x82F5790Bd1c96790E4c3a3ebC8142bD4D6F8b1CD
