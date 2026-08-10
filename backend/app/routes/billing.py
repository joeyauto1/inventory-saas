"""Billing API routes — Stripe portal, webhooks, subscription status."""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.merchant import Merchant
from app.services import stripe_service

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/portal")
async def billing_portal(merchant_id: int, db: Session = Depends(get_db)):
    """Redirect to Stripe Customer Portal for subscription management."""
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    if not merchant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer — contact support")

    portal_url = stripe_service.create_portal_session(
        customer_id=merchant.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/dashboard/settings",
    )
    return {"url": portal_url}


@router.get("/status")
async def subscription_status(merchant_id: int, db: Session = Depends(get_db)):
    """Get current subscription status for the merchant."""
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

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
            if action == "subscription_canceled":
                merchant.subscription_status = "canceled"
            elif action == "subscription_updated":
                merchant.subscription_status = result.get("status", merchant.subscription_status)
            elif action == "payment_failed":
                merchant.subscription_status = "past_due"
            elif action == "payment_succeeded":
                if merchant.subscription_status == "past_due":
                    merchant.subscription_status = "active"
            db.commit()

    return {"status": "ok", "action": action}
