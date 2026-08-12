"""Square OAuth 2.0 flow — authorization URL and code exchange."""

import httpx
from datetime import datetime, timedelta, timezone
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


class TokenExchangeError(RuntimeError):
    """A failed `POST /oauth2/token`, carrying Square's own error body.

    Square answers HTTP 401 for a wrong client secret, an expired or already-used
    authorization code, and a redirect_uri that doesn't match the one registered
    in the Developer Console. The status line alone cannot tell them apart —
    only the body can:

        {"message": "Not Authorized", "type": "service.not_authorized"}
            -> the client secret is wrong (e.g. a production secret paired with
               a sandbox application id)

        {"errors": [{"code": "UNAUTHORIZED",
                     "detail": "Authorization code not found for app ..."}]}
            -> the secret is accepted; the code is bad, expired, already spent,
               or the redirect_uri doesn't match

`raise_for_status()` discards the body, which left a real production 401
undiagnosable from the logs. This keeps it.
    """

    #: Response bodies are echoed into logs, so cap them. Square's errors are
    #: well under this; a proxy returning an HTML page is not.
    MAX_BODY_CHARS = 500

    @classmethod
    def from_response(cls, resp: httpx.Response) -> "TokenExchangeError":
        body = resp.text or "<empty body>"
        if len(body) > cls.MAX_BODY_CHARS:
            body = body[: cls.MAX_BODY_CHARS] + "… (truncated)"
        # Only the request URL and Square's own response are interpolated —
        # never our client_secret, which would otherwise land in Render's logs.
        return cls(
            f"Square token exchange failed: HTTP {resp.status_code} "
            f"from {resp.request.url} — {body}"
        )


def _require_redirect_uri() -> str:
    """Return the configured redirect URI or raise a clear error.

    A missing or wrong redirect URI sends Square an unreachable URL,
    breaking the OAuth consent screen that took hours to debug — fail
    loudly before that happens.
    """
    uri = settings.REDIRECT_URI
    if not uri:
        raise RuntimeError(
            "REDIRECT_URI is not configured. "
            "Set BACKEND_URL (or REDIRECT_URI directly) in the environment. "
            "It must match the redirect URL registered in the Square Developer Console."
        )
    return uri


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
    redirect_uri = _require_redirect_uri()
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
        f"&redirect_uri={redirect_uri}"
    )


async def exchange_code(code: str) -> dict:
    """Exchange an OAuth authorization code for tokens.

    Sends ``redirect_uri`` explicitly — OAuth 2.0 requires it in the token
    exchange when it was present in the authorization request, and omitting
    it is flagged during Square marketplace review.
    """
    redirect_uri = _require_redirect_uri()
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
                "redirect_uri": redirect_uri,
            },
        )
        if resp.is_error:
            raise TokenExchangeError.from_response(resp)
        data = resp.json()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 86400))

        return {
            "access_token": encrypt_token(data["access_token"]),
            "refresh_token": encrypt_token(data["refresh_token"]),
            "expires_at": expires_at,
            "merchant_id": data["merchant_id"],
        }
