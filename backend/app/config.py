"""Application configuration from environment variables."""

import os


class Settings:
    # Square
    SQUARE_APP_ID: str = os.environ.get("SQUARE_APP_ID", "")
    SQUARE_APP_SECRET: str = os.environ.get("SQUARE_APP_SECRET", "")
    SQUARE_WEBHOOK_SIGNATURE_KEY: str = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
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
    TRIAL_DAYS: int = 14

    # Diagnostics. Off unless explicitly enabled — /api/debug/env discloses which
    # secrets are configured and should never be reachable in normal operation.
    DEBUG_ENDPOINT_ENABLED: bool = (
        os.environ.get("DEBUG_ENDPOINT_ENABLED", "false").lower() == "true"
    )


settings = Settings()
