#!/usr/bin/env python3
"""Read-only probe of the dreamDEX perps testnet (Somnia).

Sections:
  1. REST /markets        — what a fresh client sees when it lists markets
  2. REST /tickers        — top-of-book snapshot and last trade timestamps
  3. REST /orderbooks     — one real book, 5 levels per side
  4. REST /volume         — one volume window, with the raw/decimal split
  5. WebSocket            — one request and one subscription frame on the public feed
  6. Indexer (Hideki)     — market rows with markPrice / markPriceUpdatedAt
  7. Chain + SDK          — eth_chainId of the Hideki RPC, SDK version on npm

Nothing is written, nothing is signed, no keys are used, no account is created:
every call is a public GET/POST read or a public WS read. A failure is printed
as SKIP/FAIL with the reason instead of being hidden, because the point of the
script is to record what a fresh integration actually sees on a given day.

Usage:
    python probe.py             # human-readable run
    python probe.py --json      # same run, plus a compact summary as JSON
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REST = "https://stg.api.dreamdex.io/v0"
WS = "wss://stg.api.dreamdex.io/v0/ws/public"
INDEXER = "https://hideki-dev.smk.somnia.host/v1/graphql"
HIDEKI_RPC = "https://api.hideki2.infra.testnet.somnia.network"
NPM = "https://registry.npmjs.org/@somnia-chain%2Fmarkets-sdk"
UA = "dreamdex-perps-probe/1.0 (read-only)"
CTX = ssl.create_default_context()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def http(url: str, method: str = "GET", body: dict | None = None, timeout: int = 25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"User-Agent": UA, "Accept": "application/json",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read(2_000_000)
    except urllib.error.HTTPError as e:
        return e.code, e.read(20_000)
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {str(e)[:120]}".encode()


def get_json(url: str):
    st, body = http(url)
    try:
        return st, json.loads(body)
    except Exception:
        return st, body[:300].decode("utf-8", "replace")


def head(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> int:
    summary: dict = {"probed_at": utc_now()}
    print(f"dreamDEX perps probe — {summary['probed_at']}")
    print(f"REST  {REST}")
    print(f"WS    {WS}")
    print(f"IDX   {INDEXER}")

    head("1. REST /markets")
    st, data = get_json(f"{REST}/markets")
    markets = data.get("markets") if isinstance(data, dict) else None
    print(f"GET /markets -> {st} | markets: {len(markets) if markets else 0}")
    if markets:
        for m in markets:
            print(f"  {m.get('symbol'):<14} kind={str(m.get('kind')):<6} "
                  f"tick={m.get('tickSize'):<9} lot={m.get('lotSize'):<9} minQty={m.get('minQuantity')}")
        kinds = sorted({str(m.get("kind")) for m in markets})
        print(f"  distinct kind: {kinds}")
        summary["markets"] = {"count": len(markets), "kinds": kinds}
    else:
        print(f"  body: {str(data)[:200]}")

    head("2. REST /tickers")
    st, data = get_json(f"{REST}/tickers")
    tick = data.get("symbols") if isinstance(data, dict) else None
    print(f"GET /tickers -> {st} | entries: {len(tick) if tick else 0}")
    if tick:
        for t in tick:
            print(f"  {t.get('symbol'):<14} open={t.get('open'):<10} close={t.get('close'):<10} "
                  f"high={t.get('high'):<10} low={t.get('low'):<10} vol={t.get('volume')}")
            print(f"  {'':<14} lastTradeAt={t.get('lastTradeAt')} snapshotAt={t.get('timestamp')}")
        summary["tickers"] = len(tick)

    head("3. REST /orderbooks")
    if tick:
        sym = tick[0].get("symbol")
        st, data = get_json(f"{REST}/orderbooks?symbols={urllib.parse.quote(sym)}&depth=5")
        books = data.get("orderbooks") if isinstance(data, dict) else None
        print(f"GET /orderbooks?symbols={sym}&depth=5 -> {st}")
        if books:
            b = books[0] if isinstance(books, list) else books
            bids, asks = b.get("bids") or [], b.get("asks") or []
            print(f"  bids: {[(x.get('price'), x.get('quantity')) for x in bids[:3]]}")
            print(f"  asks: {[(x.get('price'), x.get('quantity')) for x in asks[:3]]}")
            if bids and asks:
                print(f"  spread: {float(asks[0]['price']) - float(bids[0]['price']):.6f} "
                      f"({(float(asks[0]['price']) / float(bids[0]['price']) - 1) * 100:.4f}%)")
            summary["book"] = {"bids": len(bids), "asks": len(asks)}

    head("4. REST /markets/{symbol}/volume")
    if tick:
        sym = tick[0].get("symbol")
        st, data = get_json(f"{REST}/markets/{urllib.parse.quote(sym)}/volume")
        print(f"GET /markets/{sym}/volume -> {st}")
        if isinstance(data, dict):
            print(f"  baseVolume={data.get('baseVolume')} raw={data.get('baseVolumeRaw')}")
            print(f"  quoteVolume={data.get('quoteVolume')} raw={data.get('quoteVolumeRaw')}")
            print(f"  since={data.get('since')} until={data.get('until')}")
            try:
                print(f"  window={int(data['until']) - int(data['since'])} ms")
            except Exception:
                pass
            summary["volume"] = sorted(data)

    head("5. WebSocket public feed")
    try:
        import asyncio
        import websockets

        async def ws_probe():
            async with websockets.connect(WS, open_timeout=15) as ws:
                await ws.send(json.dumps({"id": 1, "operation": "getMarkets"}))
                req_frame = await asyncio.wait_for(ws.recv(), timeout=12)
                await ws.send(json.dumps({"id": 2, "operation": "subscribe", "channel": "orderbook",
                                          "params": {"symbols": [tick[0]["symbol"]]}}))
                sub_frame = await asyncio.wait_for(ws.recv(), timeout=12)
                return req_frame, sub_frame

        req_frame, sub_frame = asyncio.run(ws_probe())
        print(f"getMarkets -> {str(req_frame)[:180]}")
        print(f"subscribe  -> {str(sub_frame)[:180]}")
        summary["ws"] = "ok"
    except Exception as e:  # noqa: BLE001
        print(f"SKIP: {type(e).__name__}: {str(e)[:140]}")
        summary["ws"] = f"skip: {type(e).__name__}"

    head("6. Indexer (Hideki) — market rows")
    q = {"query": "{ Market(limit: 6) { marketId marketType baseSymbol quoteSymbol "
                  "markPrice markPriceUpdatedAt indexPrice lastPrice lastTradeAt perpStatus } }"}
    st, body = http(INDEXER, "POST", q)
    print(f"POST {INDEXER} -> {st}")
    try:
        d = json.loads(body)
        rows = (d.get("data") or {}).get("Market") or []
        if rows:
            for r in rows:
                print(f"  id={r.get('marketId')} type={r.get('marketType')} "
                      f"{r.get('baseSymbol')}/{r.get('quoteSymbol')} mark={r.get('markPrice')} "
                      f"markAt={r.get('markPriceUpdatedAt')} perpStatus={r.get('perpStatus')}")
            summary["indexer"] = {"rows": len(rows)}
        else:
            print(f"  body: {json.dumps(d, ensure_ascii=False)[:260]}")
    except Exception:
        print(f"  body: {body[:260].decode('utf-8', 'replace')}")

    head("7. Chain and SDK")
    st, body = http(HIDEKI_RPC, "POST", {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []})
    try:
        cid = json.loads(body).get("result")
        print(f"eth_chainId -> {cid} ({int(cid, 16)})")
        summary["chain_id"] = int(cid, 16)
    except Exception:
        print(f"eth_chainId SKIP -> {body[:120].decode('utf-8', 'replace')}")

    st, data = get_json(NPM)
    if isinstance(data, dict):
        ver = (data.get("dist-tags") or {}).get("latest")
        print(f"npm @somnia-chain/markets-sdk -> {ver} "
              f"(modified {(data.get('time') or {}).get('modified')})")
        summary["sdk"] = ver

    print()
    print("done — read-only: no keys, no signatures, no writes.")
    if "--json" in sys.argv:
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
