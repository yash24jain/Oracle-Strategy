# scripts/

Dependency-free readers for the live rwaUSD oracle path. **No Foundry, no npm, no pip.**
Pure-Python keccak256 + `curl` JSON-RPC. Useful on a locked-down laptop or when `foundryup` fails.

| File | What it does |
|---|---|
| `keccak.py` | Minimal FIPS-202 keccak-256 + `sel()` for function selectors. Self-tests on import. |
| `read_oracle_state.py` | OSM (`hop`, `zzz`, `stopped`, `src`, `pass`, `wards`) + adapter (`owner`, `maxDelay`, `priceFeed`, `paused`, `read`). |
| `read_feed_state.py` | Decodes the upstream Chainlink feed, the operator Safe (owners/threshold), OSM `bud` whitelist, Spotter wards. |

```bash
python scripts/read_oracle_state.py
python scripts/read_feed_state.py
```

Defaults to the public endpoint `https://ethereum-rpc.publicnode.com` — edit `RPC` at the top
of each file to use your own. Note `urllib` gets 403'd by that endpoint, hence the `curl` shim.

Verify keccak before trusting any output:

```bash
cd scripts && python -c "from keccak import keccak256,sel; \
assert keccak256(b'').hex().startswith('c5d24601'); \
assert sel('owner()')=='0x8da5cb5b'; print('ok')"
```
