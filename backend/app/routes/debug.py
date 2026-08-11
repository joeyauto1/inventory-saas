"""Debug route to check env vars are loaded."""

from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/env")
async def check_env():
    return {
        "square_app_id": settings.SQUARE_APP_ID[:20] + "..." if settings.SQUARE_APP_ID else "EMPTY",
        # SQUARE_SANDBOX is the flag that actually selects the OAuth base URL.
        # Its absence here previously made a sandbox/production mix-up invisible.
        "square_sandbox": settings.SQUARE_SANDBOX,
        "square_secret_set": bool(settings.SQUARE_APP_SECRET),
        "stripe_key_set": bool(settings.STRIPE_SECRET_KEY),
        "stripe_price_id": settings.STRIPE_PRICE_ID[:20] + "..." if settings.STRIPE_PRICE_ID else "EMPTY",
        "db_url_set": bool(settings.DATABASE_URL),
        "frontend_url": settings.FRONTEND_URL,
        "encryption_key_set": bool(settings.TOKEN_ENCRYPTION_KEY),
    }
