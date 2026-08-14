"""Square OAuth routes — login, callback, disconnect."""

import secrets
import sys
import traceback
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, HTTPException, Depends, Cookie
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

OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_STATE_MAX_AGE = 600  # 10 minutes — long enough to authorise, short enough to expire
SESSION_COOKIE = "session_token"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days — matches JWT_EXPIRE_MINUTES


def _create_jwt(merchant_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(merchant_id), "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def _log_exception(exc: Exception, correlation_id: str) -> None:
    """Log a structured error to stderr so Render's Logs tab captures it.

    Prints the exception type, message, full traceback, and correlation ID.
    The same ID is returned to the merchant so they can quote it to support.
    """
    print(
        f"[ERROR] correlation_id={correlation_id} "
        f"type={type(exc).__name__} "
        f"message={exc}",
        file=sys.stderr,
    )
    traceback.print_exc(file=sys.stderr)


@router.get("/login")
async def login():
    """Redirect merchant to Square OAuth authorization page.

    Issues a single-use CSRF state, sent both in the authorize URL and as an
    HttpOnly cookie. The callback only proceeds if the two match.
    """
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(get_auth_url(state))
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",  # Lax still sends on Square's top-level GET redirect back to us
        path="/auth",
    )
    return response


@router.get("/callback")
async def callback(
    code: str,
    state: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """Handle OAuth callback — exchange code, save merchant, redirect to dashboard.

    Failures are caught, logged with a correlation ID, and returned as a
    generic 500 so the merchant sees an actionable reference without
    internals leaking into the response body.
    """
    correlation_id = str(uuid.uuid4())

    try:
        # Verify CSRF state BEFORE doing anything with the code. Without this, an
        # attacker can complete the flow with their own Square account against a
        # victim's session.
        if not state or not oauth_state or not secrets.compare_digest(state, oauth_state):
            raise HTTPException(status_code=400, detail="Invalid OAuth state")

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

        trial_end = datetime.now(timezone.utc) + timedelta(days=settings.TRIAL_DAYS)

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

            # Create (or recover) the Stripe customer. Idempotent and keyed on
            # merchant_id in metadata, so a retry can't mint a duplicate. Any
            # failure is logged with the merchant id and the Stripe error — it
            # must never be silently swallowed again (Standards §5, §9).
            try:
                merchant.stripe_customer_id = stripe_service.get_or_create_customer(
                    merchant_id=merchant.id,
                    email=merch_info.get("merchant", {}).get("email", ""),
                    name=merch_info.get("merchant", {}).get("business_name", ""),
                )
            except Exception as exc:
                print(
                    f"[ERROR] correlation_id={correlation_id} "
                    f"merchant_id={merchant.id} "
                    f"stripe_customer_creation_failed "
                    f"type={type(exc).__name__} message={exc}",
                    file=sys.stderr,
                )

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

        # Create JWT and redirect to frontend. The token is set as an
        # HttpOnly cookie so it never appears in browser history, Referer
        # headers, or proxy logs.
        token = _create_jwt(merchant.id)
        response = RedirectResponse(
            url=f"{settings.FRONTEND_URL}/dashboard"
        )
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/",
        )
        # State is single-use — burn it so the same value can't be replayed.
        response.delete_cookie(OAUTH_STATE_COOKIE, path="/auth")
        return response

    except HTTPException:
        # FastAPI HTTPExceptions carry a status code and detail — re-raise so
        # the framework handles them normally (400 for bad state, etc.).
        raise

    except Exception as exc:
        _log_exception(exc, correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error. Reference: {correlation_id}",
        )


@router.post("/disconnect")
async def disconnect(db: Session = Depends(get_db)):
    """Placeholder for disconnect — would need merchant auth middleware."""
    return {"status": "ok"}
