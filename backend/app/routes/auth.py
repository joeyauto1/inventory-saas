"""Square OAuth routes — login, callback, disconnect."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import jwt

from app.config import settings
from app.database import get_db
from app.models.merchant import Merchant, Location
from app.services.square_auth import get_auth_url, exchange_code
from app.services.square_client import get_client, get_merchant_info, list_locations
from app.services import stripe_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_jwt(merchant_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(merchant_id), "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.get("/login")
async def login():
    """Redirect merchant to Square OAuth authorization page."""
    return RedirectResponse(get_auth_url())


@router.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    """Handle OAuth callback — exchange code, save merchant, redirect to dashboard."""
    token_data = await exchange_code(code)

    # Get merchant info and locations from Square
    client = get_client(token_data["access_token"])
    merch_info = get_merchant_info(client)
    locs = list_locations(client)

    # Upsert merchant
    merchant = (
        db.query(Merchant)
        .filter_by(square_merchant_id=token_data["merchant_id"])
        .first()
    )

    trial_end = datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)

    if merchant:
        merchant.access_token = token_data["access_token"]
        merchant.refresh_token = token_data["refresh_token"]
        merchant.token_expires_at = token_data["expires_at"]
    else:
        merchant = Merchant(
            square_merchant_id=token_data["merchant_id"],
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_expires_at=token_data["expires_at"],
            business_name=merch_info.get("merchant", {}).get("business_name", ""),
            email=merch_info.get("merchant", {}).get("email", ""),
            trial_ends_at=trial_end,
            subscription_status="trialing",
        )
        db.add(merchant)
        db.flush()

        # Create Stripe customer
        try:
            stripe_customer_id = stripe_service.create_customer(
                merchant_id=merchant.id,
                email=merch_info.get("merchant", {}).get("email", ""),
                name=merch_info.get("merchant", {}).get("business_name", ""),
            )
            merchant.stripe_customer_id = stripe_customer_id
        except Exception:
            pass  # Don't block signup if Stripe fails — they'll be prompted later

    # Upsert locations
    for loc in locs.get("locations", []):
        existing = (
            db.query(Location)
            .filter_by(square_location_id=loc["id"])
            .first()
        )
        if not existing:
            db.add(
                Location(
                    merchant_id=merchant.id,
                    square_location_id=loc["id"],
                    name=loc.get("name", ""),
                    address=loc.get("address", {}).get("address_line_1", ""),
                    timezone=loc.get("timezone", ""),
                )
            )

    db.commit()

    # Create JWT and redirect to frontend
    token = _create_jwt(merchant.id)
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/dashboard?token={token}"
    )


@router.post("/disconnect")
async def disconnect(db: Session = Depends(get_db)):
    """Placeholder for disconnect — would need merchant auth middleware."""
    return {"status": "ok"}
