"""Stripe billing service — customers, subscriptions, webhooks, portal."""

import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_customer(merchant_id: int, email: str, name: str = "") -> str:
    """Create a Stripe customer and return the customer ID."""
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"merchant_id": str(merchant_id)},
    )
    return customer.id


def create_subscription(customer_id: str, trial_days: int = 14) -> dict:
    """Create a subscription with a trial period."""
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": settings.STRIPE_PRICE_ID}],
        trial_period_days=trial_days,
        payment_behavior="default_incomplete",
    )
    return {
        "subscription_id": subscription.id,
        "status": subscription.status,
        "trial_end": subscription.trial_end,
        "client_secret": subscription.latest_invoice.payment_intent.client_secret
        if subscription.latest_invoice and subscription.latest_invoice.payment_intent
        else None,
    }


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook(payload: bytes, signature: str) -> dict:
    """Verify and process a Stripe webhook event."""
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}

    return _process_event(event)


def _process_event(event: dict) -> dict:
    """Route Stripe events to handlers."""
    event_type = event["type"]
    data = event["data"]["object"]

    handlers = {
        "customer.subscription.created": _handle_subscription_created,
        "customer.subscription.updated": _handle_subscription_updated,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_succeeded": _handle_payment_succeeded,
        "invoice.payment_failed": _handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(data)

    return {"status": "ignored", "event": event_type}


def _handle_subscription_created(subscription: dict) -> dict:
    return {
        "action": "subscription_created",
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
        "status": subscription["status"],
    }


def _handle_subscription_updated(subscription: dict) -> dict:
    return {
        "action": "subscription_updated",
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
        "status": subscription["status"],
    }


def _handle_subscription_deleted(subscription: dict) -> dict:
    return {
        "action": "subscription_canceled",
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
    }


def _handle_payment_succeeded(invoice: dict) -> dict:
    return {
        "action": "payment_succeeded",
        "invoice_id": invoice["id"],
        "customer_id": invoice["customer"],
    }


def _handle_payment_failed(invoice: dict) -> dict:
    return {
        "action": "payment_failed",
        "invoice_id": invoice["id"],
        "customer_id": invoice["customer"],
    }
