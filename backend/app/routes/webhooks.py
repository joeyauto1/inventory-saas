"""Square webhook receiver — verify signature and process inventory events."""

import hmac
import hashlib
import json

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/square")
async def square_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive and verify Square webhook events."""
    body = await request.body()
    signature = request.headers.get("x-square-signature", "")

    # Verify HMAC-SHA256 signature
    if settings.SQUARE_WEBHOOK_SIGNATURE_KEY:
        expected = hmac.new(
            settings.SQUARE_WEBHOOK_SIGNATURE_KEY.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event_type = data.get("type", "")

    if event_type == "inventory.count.updated":
        # Inventory changed — we'll process this in the sync task
        # For MVP, inventory is pulled on-demand or on page load
        # Webhook just confirms a change occurred
        pass

    return {"status": "ok"}
