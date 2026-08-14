#!/usr/bin/env python3
"""Verify Task 1 against the live deployed service.

Proves, with real terminal output:
1. /api/inventory with no credentials -> 401 (was 200 before).
2. One route in each of the other four routers -> 401.
3. /api/health still 200 (no regression).
"""
import requests

BASE = "https://inventory-saas-4.onrender.com"


def hit(method, path, body=None):
    try:
        r = requests.request(method, f"{BASE}{path}", json=body, timeout=60)
        return r.status_code, r.text[:200]
    except requests.RequestException as e:
        return -1, str(e)[:200]


def main():
    print("=== cold-start wake ===")
    s, _ = hit("GET", "/api/health")
    print(f"    /api/health -> {s}")

    print("\n=== Task 1: unauthenticated requests must be 401 ===")
    probes = [
        ("GET", "/api/inventory"),
        ("GET", "/api/inventory/V1/history"),
        ("POST", "/api/inventory/sync"),
        ("GET", "/api/billing/portal"),
        ("GET", "/api/billing/status"),
        ("POST", "/api/billing/checkout"),
        ("GET", "/api/waste"),
        ("GET", "/api/waste/summary"),
        ("GET", "/api/recipes"),
        ("GET", "/api/recipes/1"),
        ("GET", "/api/reports/waste"),
        ("GET", "/api/reports/cogs"),
        ("GET", "/api/reports/inventory-valuation"),
    ]
    failures = []
    for method, path in probes:
        s, body = hit(method, path)
        ok = s == 401
        if not ok:
            failures.append((method, path, s))
        print(f"    {method:6} {path:35} -> {s}  {'OK' if ok else 'FAIL'}")

    print("\n=== regression: health still 200 ===")
    s, body = hit("GET", "/api/health")
    print(f"    /api/health -> {s}")
    print(f"    body: {body}")

    print("\n=== no-regression: the auth hole probe ===")
    s, body = hit("GET", "/api/inventory?merchant_id=1")
    print(f"    /api/inventory?merchant_id=1 -> {s}  (baseline was 200 = THE BUG; must now be 401)")
    if s != 401:
        failures.append(("GET", "/api/inventory?merchant_id=1", s))

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("   ", f)
        raise SystemExit(1)
    print("\nALL AUTH PROBES PASS (401 everywhere unauthenticated).")


if __name__ == "__main__":
    main()
