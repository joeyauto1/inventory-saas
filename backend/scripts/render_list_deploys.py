#!/usr/bin/env python3
"""List recent deploys for the service."""
import os
import requests

SERVICE = "srv-d9sujo49v7es73fqckog"
API = f"https://api.render.com/v1/services/{SERVICE}"

def _key():
    k = os.environ.get("RENDER_API_KEY")
    if k:
        return k
    p = os.path.expanduser("~/.hermes/.env")
    for line in open(p):
        line = line.strip()
        if line.startswith("RENDER_API_KEY="):
            return line.split("=", 1)[1]
    raise SystemExit("no key")

d = requests.get(f"{API}/deploys?limit=8", headers={"Authorization": f"Bearer {_key()}"}, timeout=30).json()
for entry in d:
    dep = entry["deploy"]
    c = (dep.get("commit") or {}).get("id", "")
    m = (dep.get("commit") or {}).get("message", "").splitlines()[0][:50]
    print(f"{dep['status']:22} {c[:7]}  {m}")
