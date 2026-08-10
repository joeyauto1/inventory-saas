"""Merchant and Location models."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    square_merchant_id = Column(String(64), unique=True, nullable=False, index=True)
    access_token = Column(Text, nullable=False)  # AES-encrypted
    refresh_token = Column(Text, nullable=False)  # AES-encrypted
    token_expires_at = Column(DateTime, nullable=False)
    business_name = Column(String(255))
    email = Column(String(255))
    stripe_customer_id = Column(String(64))
    subscription_status = Column(
        String(32), default="trialing"
    )  # trialing, active, canceled, past_due
    trial_ends_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    square_location_id = Column(String(64), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    timezone = Column(String(64))
    is_active = Column(Boolean, default=True)
