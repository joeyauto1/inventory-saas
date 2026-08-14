"""Webhook action mapping must be total.

`stripe_service._process_event` maps Stripe event types to handlers that return
an `action` string. `billing.py` dispatches on those action strings to update
the merchant row. If a handler returns an action string that billing.py has no
branch for, the event is silently dropped — verified and discarded, invisible
at runtime.

The bug this pins: `_handle_subscription_created` returned
`action: "subscription_created"` while billing.py's dispatch block had no branch
for it. This test asserts every action string the service can emit is handled.
"""

from app.routes import billing
from app.services import stripe_service


def test_billing_handles_every_action_stripe_service_emits():
    emitted = set(stripe_service.ALL_ACTIONS)
    handled = set(billing.ACTION_HANDLERS.keys())

    missing = emitted - handled
    assert not missing, (
        f"billing.py has no handler for these actions: {sorted(missing)}"
    )


def test_every_stripe_event_type_has_a_handler():
    """Every event type _process_event routes must produce a known action or
    be explicitly ignored — no event type can map to None."""
    # Reconstruct the routing table exactly as _process_event builds it.
    handlers = {
        "customer.subscription.created": stripe_service._handle_subscription_created,
        "customer.subscription.updated": stripe_service._handle_subscription_updated,
        "customer.subscription.deleted": stripe_service._handle_subscription_deleted,
        "invoice.payment_succeeded": stripe_service._handle_payment_succeeded,
        "invoice.payment_failed": stripe_service._handle_payment_failed,
    }

    for event_type, handler in handlers.items():
        # Feed each handler a minimal payload and confirm the returned action
        # is one billing.py knows how to apply.
        result = handler({
            "id": "sub_test",
            "customer": "cus_test",
            "status": "active",
        })
        action = result["action"]
        assert action in billing.ACTION_HANDLERS, (
            f"event {event_type} emits action {action!r} which billing.py "
            f"does not handle"
        )


def test_subscription_created_action_is_handled():
    """Regression: the specific action that was dropped now has a handler."""
    assert "subscription_created" in billing.ACTION_HANDLERS
