import re, ssl, urllib.request
CTX=ssl.create_default_context()
for url in ("https://app.dreamdex.io/docs/developers/perps-testnet",
            "https://app.dreamdex.io/docs/welcome/making-your-first-deposit",
            "https://app.dreamdex.io/docs/welcome/quick-start"):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"probe"}), timeout=30, context=CTX) as r:
            txt=r.read(500_000).decode("utf-8","replace")
    except Exception as e:
        print(url, "ERR", str(e)[:60]); continue
    low=txt.lower()
    print("="*80); print(url, "| упоминаний faucet:", low.count("faucet"))
    for m in re.finditer(r".{0,120}faucet.{0,200}", txt, re.I):
        s=re.sub(r"<[^>]+>"," ",m.group(0)); s=re.sub(r"\s+"," ",s).strip()
        print("  …", s[:280])