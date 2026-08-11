"""Square OAuth 2.0 flow — authorization URL and code exchange."""

import httpx
from datetime import datetime, timedelta
from app.config import settings
from app.services.encryption import encrypt_token

SQUARE_AUTH_URL = "https://connect.squareup.com/oauth2/authorize"
SQUARE_TOKEN_URL = "https://connect.squareup.com/oauth2/token"
SQUARE_SANDBOX_AUTH_URL = "https://connect.squareupsandbox.com/oauth2/authorize"
SQUARE_SANDBOX_TOKEN_URL = "https://connect.squareupsandbox.com/oauth2/token"

SCOPES = [
    "INVENTORY_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "MERCHANT_PROFILE_READ",
]


def get_auth_url(state: str) -> str:
    """Build the Square OAuth authorization URL.

    `state` is echoed back by Square on the callback and must be verified
    there — it is what stops an attacker binding their Square account to
    someone else's session.

    Explicitly sets ``redirect_uri`` so the token exchange can also send it
    (required by Square's marketplace review checklist). Must match the
    redirect URL registered in the Developer Console.
    """
    scope = "+".join(SCOPES)
    base = (
        SQUARE_SANDBOX_AUTH_URL
        if settings.SQUARE_SANDBOX
        else SQUARE_AUTH_URL
    )
    return (
        f"{base}"
        f"?client_id={settings.SQUARE_APP_ID}"
        f"&scope={scope}"
        f"&state={state}"
        f"&redirect_uri={settings.REDIRECT_URI}"
    )


async def exchange_code(code: str) -> dict:
    """Exchange an OAuth authorization code for tokens.

    Sends ``redirect_uri`` explicitly — OAuth 2.0 requires it in the token
    exchange when it was present in the authorization request, and omitting
    it is flagged during Square marketplace review.
    """
    token_url = (
        SQUARE_SANDBOX_TOKEN_URL
        if settings.SQUARE_SANDBOX
        else SQUARE_TOKEN_URL
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            json={
                "client_id": settings.SQUARE_APP_ID,
                "client_secret": settings.SQUARE_APP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.REDIRECT_URI,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        expires_at = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 86400))

        return {
            "access_token": encrypt_token(data["access_token"]),
            "refresh_token": encrypt_token(data["refresh_token"]),
            "expires_at": expires_at,
            "merchant_id": data["merchant_id"],
        }
