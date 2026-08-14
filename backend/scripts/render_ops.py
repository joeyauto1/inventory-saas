#!/usr/bin/env python3
"""Render API helper — query service config and trigger deploys.

Reads RENDER_API_KEY from ~/.hermes/.env (never from the command line). Used
instead of curl so the secret never appears in shell history or process args.

Usage:
    python render_ops.py info                     # repo/branch/autodeploy
    python render_ops.py deploy <commit|branch>   # trigger a deploy
    python render_ops.py poll                     # last deploy status + commit
"""

import os
import sys
import time

import requests

RENDER_SERVICE_ID = "srv-d9sujo49v7es73fqckog"
API = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}"


def _key() -> str:
    k = os.environ.get("RENDER_API_KEY")
    if k:
        return k
    p = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line.startswith("RENDER_API_KEY="):
                return line.split("=", 1)[1]
    raise SystemExit("RENDER_API_KEY not found")


def _headers():
    return {"Authorization": f"Bearer {_key()}"}


def info():
    d = requests.get(API, headers=_headers(), timeout=30).json()
    print(f"name:       {d.get('name')}")
    print(f"type:       {d.get('type')}")
    print(f"repo:       {d.get('repo')}")
    print(f"branch:     {d.get('branch')}")
    print(f"autoDeploy: {d.get('autoDeploy')}")
    print(f"runtime:    {d.get('runtime')}")


def poll():
    d = requests.get(f"{API}/deploys?limit=1", headers=_headers(), timeout=30).json()
    dep = d[0]["deploy"]
    commit = (dep.get("commit") or {}).get("id", "")
    msg = (dep.get("commit") or {}).get("message", "")
    print(f"status: {dep['status']}")
    print(f"commit: {commit[:7] if commit else '(none)'}")
    print(f"message: {msg.splitlines()[0][:70] if msg else ''}")
    return dep


def deploy(ref: str):
    body = {"clearCache": "do_not_clear"}
    if ref.startswith(("http", "sha-")) or len(ref) == 40:
        # A 40-char hex string is a full commit SHA.
        body["commit"] = ref
    else:
        body["branch"] = ref
    r = requests.post(f"{API}/deploys", headers=_headers(), json=body, timeout=30)
    print(f"trigger: HTTP {r.status_code}")
    print(r.text[:400])


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "info":
        info()
    elif cmd == "poll":
        poll()
    elif cmd == "deploy":
        if len(sys.argv) < 3:
            raise SystemExit("usage: render_ops.py deploy <branch|commit>")
        deploy(sys.argv[2])
    else:
        raise SystemExit(f"unknown cmd {cmd}")


if __name__ == "__main__":
    main()
