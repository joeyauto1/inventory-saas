"""Billing API routes — Stripe checkout, portal, webhooks, subscription status.

Authorization: the merchant is resolved from the session JWT cookie via
``get_current_merchant``. No route accepts ``merchant_id`` from the client.
The webhook endpoint is unauthenticated — Stripe authenticates it with the
signature header — but it never trusts a client-supplied merchant id either.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Merchant
from app.services import stripe_service

router = APIRouter(prefix="/api/billing", tags=["billing"])


# Dispatch table mapping every action string stripe_service can emit to the
# handler that updates the merchant row. Kept as a module-level dict so a test
# can assert it is total against stripe_service.ALL_ACTIONS.
def _apply_subscription_created(merchant: Merchant, result: dict) -> None:
    merchant.subscription_status = result.get("status", merchant.subscription_status)


def _apply_subscription_updated(merchant: Merchant, result: dict) -> None:
    merchant.subscription_status = result.get("status", merchant.subscription_status)


def _apply_subscription_canceled(merchant: Merchant, result: dict) -> None:
    merchant.subscription_status = "canceled"


def _apply_payment_failed(merchant: Merchant, result: dict) -> None:
    merchant.subscription_status = "past_due"


def _apply_payment_succeeded(merchant: Merchant, result: dict) -> None:
    if merchant.subscription_status == "past_due":
        merchant.subscription_status = "active"


ACTION_HANDLERS = {
    stripe_service.ACTION_SUBSCRIPTION_CREATED: _apply_subscription_created,
    stripe_service.ACTION_SUBSCRIPTION_UPDATED: _apply_subscription_updated,
    stripe_service.ACTION_SUBSCRIPTION_CANCELED: _apply_subscription_canceled,
    stripe_service.ACTION_PAYMENT_FAILED: _apply_payment_failed,
    stripe_service.ACTION_PAYMENT_SUCCEEDED: _apply_payment_succeeded,
}


def _ensure_stripe_customer(merchant: Merchant, db: Session) -> str:
    """Return the merchant's Stripe customer id, creating one on demand.

    Repair path for merchants whose signup-time customer creation failed (or
    whose row predates it). Idempotent — keyed on merchant_id in metadata.
    """
    if merchant.stripe_customer_id:
        return merchant.stripe_customer_id

    customer_id = stripe_service.get_or_create_customer(
        merchant_id=merchant.id,
        email=merchant.email or "",
        name=merchant.business_name or "",
    )
    merchant.stripe_customer_id = customer_id
    db.commit()
    return customer_id


@router.post("/checkout")
async def checkout(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Create a hosted Stripe Checkout Session and return its URL.

    Subscription state is set by the webhook (the system of record), never from
    this response.
    """
    customer_id = _ensure_stripe_customer(merchant, db)
    checkout_url = stripe_service.create_checkout_session(
        customer_id=customer_id,
        price_id=settings.STRIPE_PRICE_ID,
        success_url=f"{settings.FRONTEND_URL}/dashboard/settings?checkout=success",
        cancel_url=f"{settings.FRONTEND_URL}/dashboard/settings?checkout=cancel",
    )
    return {"url": checkout_url}


@router.get("/portal")
async def billing_portal(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Redirect to Stripe Customer Portal for subscription management."""
    customer_id = _ensure_stripe_customer(merchant, db)

    portal_url = stripe_service.create_portal_session(
        customer_id=customer_id,
        return_url=f"{settings.FRONTEND_URL}/dashboard/settings",
    )
    return {"url": portal_url}


@router.get("/status")
async def subscription_status(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Get current subscription status for the merchant."""
    return {
        "status": merchant.subscription_status,
        "trial_ends_at": merchant.trial_ends_at.isoformat() if merchant.trial_ends_at else None,
    }


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Stripe webhook events and update merchant subscription state."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    result = stripe_service.handle_webhook(payload, signature)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    action = result.get("action", "")
    customer_id = result.get("customer_id", "")

    if customer_id and action:
        merchant = db.query(Merchant).filter_by(stripe_customer_id=customer_id).first()
        if merchant:
            handler = ACTION_HANDLERS.get(action)
            if handler:
                handler(merchant, result)
                db.commit()

    return {"status": "ok", "action": action}
