#!/usr/bin/env python3
"""Backfill merchant 1's missing Stripe customer.

Merchant 1 is Joey's real Square-connected sandbox merchant. Its signup-time
Stripe customer creation failed silently on 14 Aug (STRIPE_SECRET_KEY was a
pasted mask), so stripe_customer_id is NULL and it is permanently unbillable.

This script repairs it through the real code path
(stripe_service.get_or_create_customer), not by calling Stripe directly.
Idempotent — safe to run repeatedly.
"""

import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(HERE)
sys.path.insert(0, BACKEND_ROOT)

RENDER_SERVICE_ID = "srv-d9sujo49v7es73fqckog"
RENDER_API = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}"
RENDER_API_KEY_VAR = "RENDER_API_KEY"


def _render_api_key() -> str:
    k = os.environ.get(RENDER_API_KEY_VAR)
    if k:
        return k
    p = os.path.expanduser("~/.hermes/.env")
    for line in open(p):
        line = line.strip()
        if line.startswith(RENDER_API_KEY_VAR + "="):
            return line.split("=", 1)[1]
    raise SystemExit("RENDER_API_KEY not found")


def _fetch_render_env() -> dict:
    rk = _render_api_key()
    resp = requests.get(
        f"{RENDER_API}/env-vars",
        headers={"Authorization": f"Bearer {rk}"},
        timeout=30,
    )
    resp.raise_for_status()
    return {e["envVar"]["key"]: e["envVar"].get("value", "") for e in resp.json()}


def main():
    import stripe

    from app.config import settings
    from app.models.merchant import Merchant
    from app.services import stripe_service
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    env = _fetch_render_env()
    stripe_key = env.get("STRIPE_SECRET_KEY", "")
    database_url = env.get("DATABASE_URL", "")

    if not stripe_key.startswith("sk_test_"):
        raise SystemExit(f"ABORT: STRIPE_SECRET_KEY not sk_test_ (len={len(stripe_key)})")
    if not database_url:
        raise SystemExit("ABORT: DATABASE_URL empty")

    stripe.api_key = stripe_key
    stripe_service.stripe.api_key = stripe_key
    settings.STRIPE_SECRET_KEY = stripe_key

    engine = create_engine(database_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    merchant = db.query(Merchant).filter_by(id=1).first()
    if not merchant:
        raise SystemExit("merchant 1 not found in the deployed database")

    print(f"merchant 1: business_name={merchant.business_name!r} "
          f"email={merchant.email!r}")
    print(f"stripe_customer_id BEFORE = {merchant.stripe_customer_id!r}")

    if merchant.stripe_customer_id:
        print("Already populated — nothing to do.")
        return

    customer_id = stripe_service.get_or_create_customer(
        merchant_id=merchant.id,
        email=merchant.email or "",
        name=merchant.business_name or "",
    )
    merchant.stripe_customer_id = customer_id
    db.commit()

    # Read back from the DB to confirm the write landed.
    db.expire_all()
    refreshed = db.query(Merchant).filter_by(id=1).first()
    print(f"stripe_customer_id AFTER  = {refreshed.stripe_customer_id!r}")

    assert refreshed.stripe_customer_id == customer_id
    print(f"PASS: merchant 1 now has stripe_customer_id {customer_id}")


if __name__ == "__main__":
    main()
