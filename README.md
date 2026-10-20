# dreamDEX perps — read-only probe

A small, self-contained probe of the dreamDEX perps testnet on Somnia. It exists to show what a
fresh integration actually sees when it talks to the public REST API, the public WebSocket feed and
the Hideki indexer — no keys, no account, no signatures, no writes.

I used it while preparing a feedback submission for the **dreamDEX Perps Builder Bounty** (DoraHacks,
build `50043`). The submission itself is a private repository of 22 reproducible reports; this
repository only carries the probe and its recorded output, so the evidence of engagement is public
while the individual findings stay sealed until the bounty is judged.

## What was tested

| Surface | What the probe touches |
|---|---|
| REST `https://stg.api.dreamdex.io/v0` | `/markets`, `/tickers`, `/orderbooks`, `/markets/{symbol}/volume` |
| WebSocket `wss://stg.api.dreamdex.io/v0/ws/public` | `getMarkets` request and an `orderbook` subscription |
| Indexer `https://hideki-dev.smk.somnia.host/v1/graphql` | `Market` rows with `markPrice` / `markPriceUpdatedAt` / `perpStatus` |
| Chain | `eth_chainId` on the Hideki RPC |
| SDK | `@somnia-chain/markets-sdk` version from npm |

## Environment

- Somnia **Shannon** testnet for the REST API — chain id **50312**
- Somnia **Hideki** testnet for perps — chain id **50383** (`eth_chainId` → `0xc4cf`)
- REST: `https://stg.api.dreamdex.io/v0` (mainnet mirror: `https://api.dreamdex.io/v0`, chain 5031)
- SDK: `@somnia-chain/markets-sdk` **0.32.1**, Node **v24.14.1**, npm **11.11.0**
- Client: Python 3 standard library + `websockets`, `curl.exe` 8.x for spot checks
- Captured **2026-10-20 11:36 UTC** (14:36 MSK); raw run in [`probe/OUTPUT.txt`](probe/OUTPUT.txt)

## Result summary

**22 findings: 8 major, 14 normal.** Split by area:

| Area | Major | Normal | Total |
|---|---|---|---|
| SDK (`@somnia-chain/markets-sdk` 0.32.1) | 2 | 1 | 3 |
| API — REST `/v0`, WebSocket bridge, indexer | 4 | 7 | 11 |
| Docs | 2 | 6 | 8 |
| **Total** | **8** | **14** | **22** |

The API row covers the public REST surface, the WebSocket REST-bridge and the Hideki indexer (the
indexer-only items are two of the seven normal API findings).

Each report in the private set contains the exact command, the captured response, the expected
behaviour and why it matters — the same format this probe uses. Titles and reproduction steps are
deliberately not listed here.

## What the probe showed on the run above

- `/markets` answered **200** with three markets and their `tickSize` / `lotSize` / `minQuantity` fields.
- `/tickers` and `/orderbooks` answered **200** with a live book (spread 0.107% on `SOMI:USDso` at the
  time of capture), and `/markets/{symbol}/volume` returned a 604 800 000 ms window with both decimal
  and raw integer volumes.
- The WebSocket feed accepted `getMarkets` and an `orderbook` subscription in the same session.
- The indexer answered **200** with `Market` rows.
- `eth_chainId` on the Hideki RPC returned **`0xc4cf` (50383)**, and npm serves SDK **0.32.1**.

## Reproduce

```bash
python -m pip install websockets          # the only non-stdlib import
python probe/probe.py                     # human-readable
python probe/probe.py --json              # same run plus a compact JSON summary
```

The probe needs outbound access to `stg.api.dreamdex.io`, the public WebSocket, and
`hideki-dev.smk.somnia.host`. If a surface is unreachable from where you run it, the section prints
`SKIP` with the reason rather than failing the whole run — the recorded `OUTPUT.txt` is a real run
from the environment listed above, not a curated one.

## Notes

- No private keys, wallets, API keys or accounts are used anywhere in this repository.
- The probe only performs public reads; it never prepares, signs or broadcasts a transaction.
- Trade data and market metadata are public testnet data.
