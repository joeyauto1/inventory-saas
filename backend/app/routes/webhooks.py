"""Square webhook receiver — verify signature and process inventory events."""

import json

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from square.utils.webhooks_helper import verify_signature

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Square's modern HMAC-SHA256 signature header. The legacy SHA-1 header
# (`x-square-signature`) is not what Square signs with and must not be read.
SIGNATURE_HEADER = "x-square-hmacsha256-signature"


@router.post("/square")
async def square_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive and verify Square webhook events.

    Fail closed: a request is only ever processed when its HMAC-SHA256 signature
    verifies. Verification delegates to Square's own SDK helper
    (``square.utils.webhooks_helper.verify_signature``), which signs
    ``notification_url + request_body`` with HMAC-SHA256 and base64-encodes the
    result — the algorithm is not hand-rolled here. A missing key, a missing
    notification URL, a missing signature header, and a wrong signature are all
    refused.
    """
    key = settings.SQUARE_WEBHOOK_SIGNATURE_KEY
    notification_url = settings.SQUARE_NOTIFICATION_URL
    signature = request.headers.get(SIGNATURE_HEADER, "")

    if not key:
        raise HTTPException(status_code=401, detail="Webhook signature key not configured")
    if not notification_url:
        raise HTTPException(status_code=401, detail="Webhook notification URL not configured")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")

    body = (await request.body()).decode("utf-8")

    try:
        valid = verify_signature(
            request_body=body,
            signature_header=signature,
            signature_key=key,
            notification_url=notification_url,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Webhook verification misconfigured")

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(body)
    event_type = data.get("type", "")

    if event_type == "inventory.count.updated":
        # Inventory changed — we'll process this in the sync task
        # For MVP, inventory is pulled on-demand or on page load
        # Webhook just confirms a change occurred
        pass

    return {"status": "ok"}
