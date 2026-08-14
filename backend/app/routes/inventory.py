"""Inventory API routes — current stock, change history, sync.

Authorization: the merchant is resolved from the session JWT cookie via
``get_current_merchant``. No route accepts ``merchant_id`` from the client —
it is derived server-side from the authenticated session.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_merchant
from app.models.merchant import Location, Merchant
from app.services.square_client import (
    get_client,
    get_inventory_changes,
    get_inventory_counts,
    list_catalog_items,
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
async def get_inventory(
    location_id: int = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Get current inventory levels for the merchant, with optional location filter."""
    client = get_client(merchant.access_token)

    # Pull all catalog items
    catalog = list_catalog_items(client)
    items = catalog.get("objects", [])

    # Get location IDs
    locations = (
        db.query(Location).filter_by(merchant_id=merchant.id, is_active=True).all()
    )
    loc_ids = [loc.square_location_id for loc in locations]
    if location_id:
        loc = db.query(Location).filter_by(id=location_id, merchant_id=merchant.id).first()
        if loc:
            loc_ids = [loc.square_location_id]

    # Build list of catalog object IDs (item variations that track inventory)
    catalog_ids = []
    item_map = {}
    for obj in items:
        if obj.get("type") == "ITEM":
            for var in obj.get("item_data", {}).get("variations", []):
                vid = var.get("id")
                catalog_ids.append(vid)
                item_map[vid] = {
                    "item_name": obj.get("item_data", {}).get("name", ""),
                    "variation_name": var.get("item_variation_data", {}).get("name", ""),
                    "category": "",  # Would need category lookup
                }

    if not catalog_ids:
        return {"items": [], "count": 0}

    # Get inventory counts
    counts_data = get_inventory_counts(client, catalog_ids, loc_ids)
    counts = counts_data.get("counts", [])

    # Merge catalog data with inventory counts
    result = []
    for count in counts:
        cid = count.get("catalog_object_id", "")
        info = item_map.get(cid, {})
        qty = int(float(count.get("quantity", "0")))
        result.append(
            {
                "catalog_object_id": cid,
                "item_name": info.get("item_name", ""),
                "variation_name": info.get("variation_name", ""),
                "quantity": qty,
                "status": "out" if qty <= 0 else "low" if qty < 10 else "ok",
                "location_id": count.get("location_id", ""),
                "calculated_at": count.get("calculated_at", ""),
            }
        )

    return {"items": result, "count": len(result)}


@router.get("/{catalog_object_id}/history")
async def get_inventory_history(
    catalog_object_id: str,
    location_id: int = None,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Get inventory change history for a specific item."""
    client = get_client(merchant.access_token)

    loc_ids = None
    if location_id:
        loc = db.query(Location).filter_by(id=location_id, merchant_id=merchant.id).first()
        if loc:
            loc_ids = [loc.square_location_id]

    changes = get_inventory_changes(client, [catalog_object_id], loc_ids)
    return {"changes": changes.get("changes", []), "catalog_object_id": catalog_object_id}


@router.post("/sync")
async def sync_inventory(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    """Trigger a full re-sync from Square (delegates to get_inventory)."""
    return await get_inventory(merchant=merchant, db=db)
