"""Square OAuth 2.0 flow — authorization URL and code exchange."""

import httpx
from datetime import datetime, timedelta
from app.config import settings
from app.services.encryption import encrypt_token

SQUARE_AUTH_URL = "https://connect.squareup.com/oauth2/authorize"
SQUARE_TOKEN_URL = "https://connect.squareup.com/oauth2/token"

SCOPES = [
    "INVENTORY_READ",
    "ITEMS_READ",
    "ORDERS_READ",
    "MERCHANT_PROFILE_READ",
]


def get_auth_url() -> str:
    """Build the Square OAuth authorization URL."""
    scope = "+".join(SCOPES)
    base = "https://connect.squareup.com/oauth2/authorize"
    return (
        f"{base}"
        f"?client_id={settings.SQUARE_APP_ID}"
        f"&scope={scope}"
        f"&session=false"
    )


async def exchange_code(code: str) -> dict:
    """Exchange an OAuth authorization code for tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SQUARE_TOKEN_URL,
            json={
                "client_id": settings.SQUARE_APP_ID,
                "client_secret": settings.SQUARE_APP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
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
