"""Shared FastAPI dependencies — session auth and current-merchant resolution.

The merchant identity comes exclusively from the signed `session_token` cookie
set at OAuth login. A client-supplied `merchant_id` is never accepted anywhere:
no route signature takes it from the path, query string, or request body.
"""

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.merchant import Merchant

# The canonical name of the session cookie. Set by auth.login/callback with
# HttpOnly + Secure + SameSite=Lax. Kept here (not in auth.py) so the auth
# dependency and the auth routes share one source of truth without a cycle.
SESSION_COOKIE = "session_token"


def get_current_merchant(
    request: Request,
    db: Session = Depends(get_db),
) -> Merchant:
    """Resolve the current merchant from the session JWT cookie only.

    Returns the ``Merchant`` row the caller is authenticated as. Raises 401
    when the cookie is missing, malformed, expired, or references a merchant
    that no longer exists. The identity is never read from the request body,
    query string, or path — only from the signed cookie.
    """
    session_token = request.cookies.get(SESSION_COOKIE)

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            session_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid session")

    try:
        merchant_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session")

    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid session")

    return merchant
