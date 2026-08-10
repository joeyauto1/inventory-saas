"""Waste tracking API routes — log waste events, list, aggregate."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models.waste import WasteEvent

router = APIRouter(prefix="/api/waste", tags=["waste"])

VALID_REASONS = ["spoilage", "overprep", "dropped", "expired", "trim", "other"]


class WasteLogRequest(BaseModel):
    merchant_id: int
    location_id: int
    square_catalog_object_id: str
    item_name: str
    quantity: float
    reason: str
    variation_name: str = ""
    unit: str = "each"
    cost_per_unit: float = 0.0
    notes: str = ""


@router.post("")
async def log_waste(body: WasteLogRequest, db: Session = Depends(get_db)):
    """Record a waste event."""
    if body.reason not in VALID_REASONS:
        raise HTTPException(status_code=400, detail=f"Invalid reason. Must be one of: {VALID_REASONS}")

    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    total_cost = round(body.quantity * (body.cost_per_unit or 0), 2)

    event = WasteEvent(
        merchant_id=body.merchant_id,
        location_id=body.location_id,
        square_catalog_object_id=body.square_catalog_object_id,
        item_name=body.item_name,
        variation_name=body.variation_name,
        quantity=body.quantity,
        unit=body.unit,
        reason=body.reason,
        cost_per_unit=body.cost_per_unit or 0,
        total_cost=total_cost,
        notes=body.notes,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {"status": "ok", "event": {"id": event.id, "total_cost": str(event.total_cost)}}


@router.get("")
async def list_waste(
    merchant_id: int,
    location_id: int = None,
    reason: str = None,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """List waste events with optional filters."""
    query = db.query(WasteEvent).filter_by(merchant_id=merchant_id)

    if location_id:
        query = query.filter_by(location_id=location_id)
    if reason:
        query = query.filter_by(reason=reason)

    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = query.filter(WasteEvent.recorded_at >= cutoff)

    query = query.order_by(WasteEvent.recorded_at.desc())
    events = query.limit(200).all()

    return {
        "events": [
            {
                "id": e.id,
                "item_name": e.item_name,
                "variation_name": e.variation_name,
                "quantity": str(e.quantity),
                "unit": e.unit,
                "reason": e.reason,
                "total_cost": str(e.total_cost),
                "notes": e.notes,
                "recorded_at": e.recorded_at.isoformat() if e.recorded_at else "",
            }
            for e in events
        ]
    }


@router.get("/summary")
async def waste_summary(
    merchant_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregated waste summary: total cost by reason, top wasted items."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    by_reason = (
        db.query(
            WasteEvent.reason,
            func.sum(WasteEvent.total_cost).label("total"),
            func.count(WasteEvent.id).label("count"),
        )
        .filter(WasteEvent.merchant_id == merchant_id)
        .filter(WasteEvent.recorded_at >= cutoff)
        .group_by(WasteEvent.reason)
        .all()
    )

    top_items = (
        db.query(
            WasteEvent.item_name,
            func.sum(WasteEvent.total_cost).label("total"),
            func.sum(WasteEvent.quantity).label("qty"),
        )
        .filter(WasteEvent.merchant_id == merchant_id)
        .filter(WasteEvent.recorded_at >= cutoff)
        .group_by(WasteEvent.item_name)
        .order_by(func.sum(WasteEvent.total_cost).desc())
        .limit(10)
        .all()
    )

    grand_total = (
        db.query(func.sum(WasteEvent.total_cost))
        .filter(WasteEvent.merchant_id == merchant_id)
        .filter(WasteEvent.recorded_at >= cutoff)
        .scalar()
    ) or 0

    return {
        "period_days": days,
        "grand_total": str(grand_total),
        "by_reason": [
            {"reason": r[0], "total": str(r[1] or 0), "count": r[2]}
            for r in by_reason
        ],
        "top_items": [
            {"item_name": r[0], "total_cost": str(r[1] or 0), "total_quantity": str(r[2] or 0)}
            for r in top_items
        ],
    }


@router.delete("/{event_id}")
async def delete_waste(event_id: int, merchant_id: int, db: Session = Depends(get_db)):
    """Delete a waste event (undo)."""
    event = db.query(WasteEvent).filter_by(id=event_id, merchant_id=merchant_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Waste event not found")
    db.delete(event)
    db.commit()
    return {"status": "deleted"}
