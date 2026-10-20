import re, ssl, urllib.request
CTX=ssl.create_default_context()
with urllib.request.urlopen(urllib.request.Request("https://app.dreamdex.io/docs/welcome/quick-start", headers={"User-Agent":"probe"}), timeout=30, context=CTX) as r:
    txt=r.read(500_000).decode("utf-8","replace")
urls=sorted(set(re.findall(r"https?://[a-z0-9.\-]*(?:faucet|somnia)[a-z0-9.\-/]*", txt, re.I)))
print("faucet/somnia links:")
for u in urls: print("  ", u)
m=re.findall(r"0x[0-9a-fA-F]{40}", txt)
print("\ncontracts mentioned:", sorted(set(m))[:6])