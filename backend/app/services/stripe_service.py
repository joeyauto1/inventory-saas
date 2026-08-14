"""Stripe billing service — customers, subscriptions, webhooks, portal, checkout."""

import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# The full set of action strings this service can emit from _process_event.
# billing.py must have a matching branch for every one of these — a test
# asserts the mapping is total so a new action can never be silently dropped.
ACTION_SUBSCRIPTION_CREATED = "subscription_created"
ACTION_SUBSCRIPTION_UPDATED = "subscription_updated"
ACTION_SUBSCRIPTION_CANCELED = "subscription_canceled"
ACTION_PAYMENT_SUCCEEDED = "payment_succeeded"
ACTION_PAYMENT_FAILED = "payment_failed"

ALL_ACTIONS = frozenset(
    {
        ACTION_SUBSCRIPTION_CREATED,
        ACTION_SUBSCRIPTION_UPDATED,
        ACTION_SUBSCRIPTION_CANCELED,
        ACTION_PAYMENT_SUCCEEDED,
        ACTION_PAYMENT_FAILED,
    }
)


def create_customer(merchant_id: int, email: str, name: str = "") -> str:
    """Create a Stripe customer tagged with our merchant_id and return the ID."""
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"merchant_id": str(merchant_id)},
    )
    return customer.id


def _find_customer_by_merchant(merchant_id: int) -> str | None:
    """Return an existing Stripe customer id for merchant_id, or None.

    Idempotency guard: a retry after a crash (create succeeded, DB write did
    not) must not mint a duplicate customer. Customers are keyed on merchant_id
    in metadata. Tries Stripe's Search API first, then falls back to listing.
    """
    key = str(merchant_id)
    try:
        result = stripe.Customer.search(
            query=f"metadata['merchant_id']:'{key}'",
            limit=1,
        )
        if result.data:
            return result.data[0].id
    except stripe.StripeError:
        # Search may be unavailable on this account — fall through to listing.
        pass

    for customer in stripe.Customer.list(limit=100).auto_paging_iter():
        # StripeObject has no .get(); metadata is an UntypedStripeObject keyed by
        # attribute access. getattr with a default is the safe read.
        md = getattr(customer, "metadata", None)
        if md and getattr(md, "merchant_id", None) == key:
            return customer.id
    return None


def get_or_create_customer(merchant_id: int, email: str = "", name: str = "") -> str:
    """Return the merchant's Stripe customer, creating it if absent.

    Idempotent and keyed on merchant_id in customer metadata, so repeated calls
    (or a retry after a partial failure) never create a duplicate.
    """
    existing = _find_customer_by_merchant(merchant_id)
    if existing:
        return existing
    return create_customer(merchant_id, email=email, name=name)


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a hosted Stripe Checkout Session and return its URL.

    Checkout is preferred over create_subscription() + default_incomplete: it is
    hosted by Stripe, handles SCA and card collection, and requires no card UI
    in our frontend. Subscription state is set by the webhook, not here.
    """
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    # A successfully created Checkout Session always carries a URL. Guard against
    # a None from the SDK type stubs so the contract stays "str".
    if not session.url:
        raise RuntimeError("Stripe returned a Checkout Session with no URL")
    return session.url


def create_subscription(
    customer_id: str,
    default_payment_method: str | None = None,
    trial_days: int | None = None,
) -> dict:
    """Create a subscription, optionally completing immediately with a card.

    NOTE: the production user journey is hosted Checkout (see
    ``create_checkout_session``). This function exists for the API-driven smoke
    test, which attaches a test card directly and creates a subscription without
    a browser. When ``default_payment_method`` is given, Stripe charges it
    immediately and the subscription goes active; the resulting webhook updates
    the merchant row.
    """
    kwargs = {
        "customer": customer_id,
        "items": [{"price": settings.STRIPE_PRICE_ID}],
    }
    if default_payment_method:
        kwargs["default_payment_method"] = default_payment_method
    if trial_days:
        kwargs["trial_period_days"] = trial_days

    subscription = stripe.Subscription.create(**kwargs)
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
        "action": ACTION_SUBSCRIPTION_CREATED,
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
        "status": subscription["status"],
    }


def _handle_subscription_updated(subscription: dict) -> dict:
    return {
        "action": ACTION_SUBSCRIPTION_UPDATED,
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
        "status": subscription["status"],
    }


def _handle_subscription_deleted(subscription: dict) -> dict:
    return {
        "action": ACTION_SUBSCRIPTION_CANCELED,
        "subscription_id": subscription["id"],
        "customer_id": subscription["customer"],
    }


def _handle_payment_succeeded(invoice: dict) -> dict:
    return {
        "action": ACTION_PAYMENT_SUCCEEDED,
        "invoice_id": invoice["id"],
        "customer_id": invoice["customer"],
    }


def _handle_payment_failed(invoice: dict) -> dict:
    return {
        "action": ACTION_PAYMENT_FAILED,
        "invoice_id": invoice["id"],
        "customer_id": invoice["customer"],
    }
