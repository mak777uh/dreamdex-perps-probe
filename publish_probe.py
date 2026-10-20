import base64, json, ssl, subprocess, urllib.error, urllib.request
from pathlib import Path

REPO = "dreamdex-perps-probe"
DIR = Path(r"C:\111\agents\verifier\dreamdex-probe")
TOK = open(r"C:\111\env\secrets\github-config\token.txt", encoding="utf-8").read().strip()
CTX = ssl.create_default_context()


def gh(path, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request("https://api.github.com" + path, data=data, method=method,
                                 headers={"User-Agent": "dsh-agent", "Accept": "application/vnd.github+json",
                                          "Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
            return r.status, r.read(400000)
    except urllib.error.HTTPError as e:
        return e.code, e.read(4000)


st, b = gh("/user")
user = json.loads(b)["login"]
print("user:", user)

st, b = gh(f"/repos/{user}/{REPO}")
if st == 404:
    st, b = gh("/user/repos", "POST", {
        "name": REPO, "private": False,
        "description": "Read-only probe of the dreamDEX perps testnet (Somnia): REST, WebSocket, indexer, SDK",
        "has_issues": True, "has_wiki": False, "has_projects": False})
    print("create repo:", st, json.loads(b).get("html_url") if st == 201 else b[:200])
else:
    print("repo exists:", st)

subprocess.run(["git", "init", "-q"], cwd=DIR, check=False)
subprocess.run(["git", "checkout", "-q", "-B", "main"], cwd=DIR, check=False)
subprocess.run(["git", "add", "-A"], cwd=DIR, check=False)
subprocess.run(["git", "-c", "user.name=mak777uh", "-c", "user.email=mak777uh@users.noreply.github.com",
                "commit", "-q", "-m", "Read-only dreamDEX perps probe: REST, WebSocket, indexer, SDK"], cwd=DIR,
               check=False)
b64 = base64.b64encode(f"x-access-token:{TOK}".encode()).decode()
r = subprocess.run(["git", "-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {b64}",
                    "push", "-f", f"https://github.com/{user}/{REPO}.git", "main"],
                   cwd=DIR, capture_output=True, text=True, encoding="utf-8")
print("push:", r.returncode, (r.stdout or "").strip()[-160:], (r.stderr or "").strip()[-200:])
print("URL: https://github.com/%s/%s" % (user, REPO))
