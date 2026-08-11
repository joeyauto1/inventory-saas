"""Reporting API routes — waste reports, COGS, inventory valuation."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.waste import WasteEvent
from app.models.merchant import Merchant
from app.services.square_client import get_client, list_catalog_items, get_inventory_counts

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/waste")
async def waste_report(
    merchant_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Waste report: total cost, breakdown by reason, top wasted items."""
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total waste cost
    total = (
        db.query(func.sum(WasteEvent.total_cost))
        .filter(WasteEvent.merchant_id == merchant_id)
        .filter(WasteEvent.recorded_at >= cutoff)
        .scalar()
    ) or 0

    # By reason
    by_reason = (
        db.query(
            WasteEvent.reason,
            func.sum(WasteEvent.total_cost).label("total"),
            func.count(WasteEvent.id).label("count"),
        )
        .filter(WasteEvent.merchant_id == merchant_id)
        .filter(WasteEvent.recorded_at >= cutoff)
        .group_by(WasteEvent.reason)
        .order_by(func.sum(WasteEvent.total_cost).desc())
        .all()
    )

    # Top 10 wasted items
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

    return {
        "period_days": days,
        "total_waste_cost": str(total),
        "by_reason": [
            {"reason": r[0], "total": str(r[1] or 0), "count": r[2]}
            for r in by_reason
        ],
        "top_items": [
            {"item_name": r[0], "total_cost": str(r[1] or 0), "total_quantity": str(r[2] or 0)}
            for r in top_items
        ],
    }


@router.get("/cogs")
async def cogs_estimate(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    """Theoretical COGS based on recipe costs and recent sales data.
    
    For MVP, this returns a basic inventory valuation since we don't
    pull order data from Square yet. Full COGS will need order history
    cross-referenced with recipe costs.
    """
    # Placeholder — full COGS needs order data
    return {
        "status": "coming_soon",
        "note": "COGS requires order history integration (post-MVP). "
                "Use recipe costing for per-plate calculations.",
    }


@router.get("/inventory-valuation")
async def inventory_valuation(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    """Estimate total inventory value based on current stock from Square."""
    merchant = db.query(Merchant).filter_by(id=merchant_id).first()
    if not merchant:
        return {"error": "Merchant not found"}

    client = get_client(merchant.access_token)

    # Pull catalog to get item variations
    catalog = list_catalog_items(client)
    items = catalog.get("objects", [])

    catalog_ids = []
    for obj in items:
        if obj.get("type") == "ITEM":
            for var in obj.get("item_data", {}).get("variations", []):
                catalog_ids.append(var.get("id"))

    if not catalog_ids:
        return {"total_value": "0", "item_count": 0}

    # Get inventory counts
    counts_data = get_inventory_counts(client, catalog_ids)
    counts = counts_data.get("counts", [])

    total_items = sum(int(float(c.get("quantity", "0"))) for c in counts)

    return {
        "total_items_in_stock": total_items,
        "catalog_items_tracked": len(catalog_ids),
        "note": "Dollar valuation requires cost data from purchase orders or manual entry (post-MVP).",
    }
