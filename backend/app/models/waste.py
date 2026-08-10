"""Waste event model."""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.sql import func
from app.database import Base


class WasteEvent(Base):
    __tablename__ = "waste_events"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    location_id = Column(Integer, nullable=False, index=True)
    square_catalog_object_id = Column(String(64), nullable=False)
    item_name = Column(String(255), nullable=False)
    variation_name = Column(String(255))
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(32), default="each")
    reason = Column(
        String(64), nullable=False
    )  # spoilage, overprep, dropped, expired, trim, other
    cost_per_unit = Column(Numeric(10, 4))  # in smallest currency unit (cents)
    total_cost = Column(Numeric(10, 2))  # in smallest currency unit (cents)
    notes = Column(Text)
    recorded_at = Column(DateTime, server_default=func.now())
