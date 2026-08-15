"""Application configuration from environment variables."""

import os


class Settings:
    # Square
    SQUARE_APP_ID: str = os.environ.get("SQUARE_APP_ID", "")
    SQUARE_APP_SECRET: str = os.environ.get("SQUARE_APP_SECRET", "")
    SQUARE_WEBHOOK_SIGNATURE_KEY: str = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
    # The webhook notification URL as registered in the Square Developer Console.
    # It is part of the signed payload (verify_signature signs notification_url +
    # request_body), so verification cannot work unless this matches the Console
    # registration exactly.
    SQUARE_NOTIFICATION_URL: str = os.environ.get("SQUARE_NOTIFICATION_URL", "")
    SQUARE_SANDBOX: bool = os.environ.get("SQUARE_SANDBOX", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://localhost:5432/inventory_saas",
    )

    # Token encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    TOKEN_ENCRYPTION_KEY: str = os.environ.get("TOKEN_ENCRYPTION_KEY", "")

    # JWT for session
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Stripe
    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID: str = os.environ.get("STRIPE_PRICE_ID", "")

    # App
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    # The backend's own public URL — used for OAuth redirects and webhook
    # registration. Must be set to the Render service URL in production
    # (e.g. https://inventory-saas-4.onrender.com).
    BACKEND_URL: str = os.environ.get("BACKEND_URL", "")
    TRIAL_DAYS: int = 14

    # OAuth redirect URI — must match exactly what is registered in the
    # Square Developer Console under OAuth > Redirect URL. Set explicitly
    # via REDIRECT_URI, or leave unset and it will be computed from
    # BACKEND_URL. If neither provides a value the OAuth routes will raise
    # a clear error at call time rather than sending Square a wrong URL.
    REDIRECT_URI: str = os.environ.get(
        "REDIRECT_URI",
        f"{BACKEND_URL}/auth/callback" if BACKEND_URL else "",
    )

    # Diagnostics. Off unless explicitly enabled — /api/debug/env discloses which
    # secrets are configured and should never be reachable in normal operation.
    DEBUG_ENDPOINT_ENABLED: bool = (
        os.environ.get("DEBUG_ENDPOINT_ENABLED", "false").lower() == "true"
    )


settings = Settings()
