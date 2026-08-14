#!/usr/bin/env python3
"""End-to-end billing smoke test against the DEPLOYED service.

Drives the real billing chain without a browser:

1. Creates a disposable test merchant in the deployed database.
2. Creates the Stripe customer through the real Task 3 code path
   (``stripe_service.get_or_create_customer``), not by calling Stripe directly.
3. Attaches the ``pm_card_visa`` test card and sets it as the default.
4. Creates a subscription against STRIPE_PRICE_ID through the real
   ``stripe_service.create_subscription`` code path.
5. Polls the deployed database until the webhook (the system of record) updates
   the merchant's ``subscription_status``, then asserts it changed.
6. Prints a summary and supports ``--cleanup``.

Credentials are pulled from Render (never from a local file): STRIPE_SECRET_KEY,
DATABASE_URL, and STRIPE_PRICE_ID are read from the service's env-vars via the
Render API. The key is verified to be ``sk_test_``-prefixed before any call —
this account is in test mode and must stay there. If ``livemode`` is ever true,
the script aborts.

Usage (from the backend directory):

    ./venv/bin/python scripts/billing_smoke_test.py
    ./venv/bin/python scripts/billing_smoke_test.py --cleanup

The webhook arrives at the DEPLOYED service (inventory-saas-4.onrender.com),
which is what updates the merchant row. This script therefore reads the merchant
status back from the deployed database — the same one the webhook writes.
"""

import argparse
import os
import sys
import time
import uuid

import requests

# Backend repo root = parent of scripts/. Add it to the path so `app` imports.
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(HERE)
sys.path.insert(0, BACKEND_ROOT)

RENDER_SERVICE_ID = "srv-d9sujo49v7es73fqckog"
RENDER_API = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}"

SMOKE_BUSINESS_NAME = "SMOKE TEST — safe to delete"


def _render_api_key() -> str:
    key = os.environ.get("RENDER_API_KEY")
    if key:
        return key
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("RENDER_API_KEY="):
                return line.split("=", 1)[1]
    raise SystemExit("RENDER_API_KEY not found in env or ~/.hermes/.env")


def _fetch_render_env(key: str) -> dict[str, str]:
    """Fetch the service's env-vars from Render and return {NAME: value}."""
    rk = _render_api_key()
    resp = requests.get(
        f"{RENDER_API}/env-vars",
        headers={"Authorization": f"Bearer {rk}"},
        timeout=30,
    )
    resp.raise_for_status()
    env = {}
    for entry in resp.json():
        ev = entry["envVar"]
        env[ev["key"]] = ev.get("value", "")
    return env


def _connect_db(database_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _create_merchant(Session, stripe_customer_id: str | None = None):
    from datetime import datetime, timedelta, timezone

    from app.models.merchant import Merchant

    db = Session()
    now = datetime.now(timezone.utc)
    merchant = Merchant(
        square_merchant_id=f"smoke-{uuid.uuid4().hex[:16]}",
        access_token="smoke-test-not-a-real-token",
        refresh_token="smoke-test-not-a-real-token",
        token_expires_at=now + timedelta(days=30),
        business_name=SMOKE_BUSINESS_NAME,
        email="smoke-test@example.com",
        trial_ends_at=now + timedelta(days=14),
        subscription_status="trialing",
        stripe_customer_id=stripe_customer_id,
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    merchant_id = merchant.id
    db.close()
    return merchant_id


def _set_merchant_stripe_customer(Session, merchant_id: int, customer_id: str):
    from app.models.merchant import Merchant

    db = Session()
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    merchant.stripe_customer_id = customer_id
    db.commit()
    db.close()


def _read_merchant(Session, merchant_id: int):
    from app.models.merchant import Merchant

    db = Session()
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        db.close()
        return None
    result = {
        "id": merchant.id,
        "stripe_customer_id": merchant.stripe_customer_id,
        "subscription_status": merchant.subscription_status,
    }
    db.close()
    return result


def _delete_merchant(Session, merchant_id: int):
    from app.models.merchant import Merchant

    db = Session()
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if merchant:
        db.delete(merchant)
        db.commit()
    db.close()


def _run(cleanup_only: bool = False):
    import stripe

    from app.services import stripe_service

    print("=== fetching credentials from Render ===")
    env = _fetch_render_env("env-vars")

    stripe_key = env.get("STRIPE_SECRET_KEY", "")
    database_url = env.get("DATABASE_URL", "")
    price_id = env.get("STRIPE_PRICE_ID", "")

    # Standard §11 — validate shape, not presence.
    if not stripe_key.startswith("sk_test_"):
        raise SystemExit(
            f"ABORT: STRIPE_SECRET_KEY is not sk_test_-prefixed (len={len(stripe_key)}). "
            "This account is in test mode and must stay there."
        )
    if not database_url:
        raise SystemExit("ABORT: DATABASE_URL is empty on Render.")
    if not price_id:
        raise SystemExit("ABORT: STRIPE_PRICE_ID is empty on Render.")

    print(f"    STRIPE_SECRET_KEY   sk_test_… (len={len(stripe_key)})")
    print(f"    STRIPE_PRICE_ID     {price_id}")
    print(f"    DATABASE_URL        set (len={len(database_url)})")

    # Point the real code paths at the fetched credentials.
    stripe.api_key = stripe_key
    stripe_service.stripe.api_key = stripe_key
    from app.config import settings

    settings.STRIPE_SECRET_KEY = stripe_key
    settings.STRIPE_PRICE_ID = price_id

    # livemode guard — never create a live object. The sk_test_ prefix check
    # above is the primary gate; this is the secondary check on a real object.
    # Account.retrieve() exposes livemode inconsistently across API versions,
    # so we read it from the created customer below (before any charge) instead.
    print(f"    livemode             (checked on created customer)")

    Session = _connect_db(database_url)

    # Find the merchant to clean up (if any) and delete it.
    if cleanup_only:
        from app.models.merchant import Merchant

        db = Session()
        matches = db.query(Merchant).filter_by(business_name=SMOKE_BUSINESS_NAME).all()
        db.close()
        if not matches:
            print("No SMOKE TEST merchants found — nothing to clean up.")
            return
        for m in matches:
            # Cancel any active subscription for this merchant's customer.
            if m.stripe_customer_id:
                try:
                    subs = stripe.Subscription.list(
                        customer=m.stripe_customer_id, status="all", limit=10
                    )
                    for sub in subs.auto_paging_iter():
                        stripe.Subscription.cancel(sub.id)
                        print(f"    canceled subscription {sub.id}")
                except stripe.StripeError as exc:
                    print(f"    (could not cancel subs: {exc})")
                try:
                    stripe.Customer.delete(m.stripe_customer_id)
                    print(f"    deleted customer {m.stripe_customer_id}")
                except stripe.StripeError as exc:
                    print(f"    (could not delete customer: {exc})")
            _delete_merchant(Session, m.id)
            print(f"    deleted merchant {m.id}")
        print("Cleanup complete.")
        return

    print("=== creating disposable test merchant ===")
    merchant_id = _create_merchant(Session)
    print(f"    merchant_id = {merchant_id}  (business_name='{SMOKE_BUSINESS_NAME}')")

    print("=== creating Stripe customer via the real Task 3 code path ===")
    customer_id = stripe_service.get_or_create_customer(
        merchant_id=merchant_id,
        email="smoke-test@example.com",
        name=SMOKE_BUSINESS_NAME,
    )
    _set_merchant_stripe_customer(Session, merchant_id, customer_id)
    print(f"    stripe_customer_id = {customer_id}")

    # livemode guard on the real object, before any charge is made.
    customer = stripe.Customer.retrieve(customer_id)
    if getattr(customer, "livemode", False):
        raise SystemExit("ABORT: created customer is in live mode. Test mode only.")
    print(f"    livemode             {getattr(customer, 'livemode', None)}")

    print("=== attaching test card pm_card_visa as default ===")
    pm = stripe.PaymentMethod.attach("pm_card_visa", customer=customer_id)
    stripe.Customer.modify(
        customer_id,
        invoice_settings={"default_payment_method": pm.id},
    )
    print(f"    payment_method = {pm.id} (attached + default)")

    print("=== creating subscription via the real code path ===")
    sub = stripe_service.create_subscription(
        customer_id=customer_id,
        default_payment_method=pm.id,
    )
    subscription_id = sub["subscription_id"]
    print(f"    subscription_id = {subscription_id}")
    print(f"    stripe-reported status = {sub['status']}")

    print("=== waiting for the webhook to update the merchant row ===")
    before = _read_merchant(Session, merchant_id)
    if not before:
        raise SystemExit("FAIL: could not read the test merchant back from the DB.")
    print(f"    status BEFORE webhook = {before['subscription_status']!r}")

    after = before
    deadline = time.time() + 90
    while time.time() < deadline:
        time.sleep(3)
        after = _read_merchant(Session, merchant_id)
        if after and after["subscription_status"] != before["subscription_status"]:
            break

    if not after:
        raise SystemExit("FAIL: test merchant disappeared from the DB mid-run.")
    print(f"    status AFTER webhook  = {after['subscription_status']!r}")

    # The webhook is the system of record — assert against it, not the API.
    if after["subscription_status"] == before["subscription_status"]:
        raise SystemExit(
            "FAIL: merchant subscription_status did not change after 90s. "
            "The webhook was not observed updating the row."
        )

    print("=== SUMMARY ===")
    print(f"    merchant_id         = {merchant_id}")
    print(f"    stripe_customer_id  = {customer_id}")
    print(f"    subscription_id     = {subscription_id}")
    print(f"    subscription_status = {before['subscription_status']!r} -> {after['subscription_status']!r}")
    print("PASS: webhook updated the merchant row.")


def main():
    parser = argparse.ArgumentParser(description="Billing smoke test (deployed service)")
    parser.add_argument("--cleanup", action="store_true", help="delete test merchants and cancel test subs")
    args = parser.parse_args()
    _run(cleanup_only=args.cleanup)


if __name__ == "__main__":
    main()
