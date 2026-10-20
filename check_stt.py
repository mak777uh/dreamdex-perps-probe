import json, urllib.request, ssl
CTX=ssl.create_default_context()
body={"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["0x0A66a9dEF221Efc698b6bbecA82cAE6729A8aba8","latest"]}
r=urllib.request.Request("https://api.hideki2.infra.testnet.somnia.network", data=json.dumps(body).encode(), headers={"Content-Type":"application/json","User-Agent":"probe"})
with urllib.request.urlopen(r, timeout=25, context=CTX) as resp:
    d=json.loads(resp.read())
print("Hideki balance:", d)