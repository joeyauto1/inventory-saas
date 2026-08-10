"""Recipe and recipe ingredient models."""

from sqlalchemy import Column, Integer, String, Numeric, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    selling_price = Column(Numeric(10, 2))  # in smallest currency unit (cents)
    portions = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    square_catalog_object_id = Column(String(64), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 4), nullable=False)
    unit = Column(String(32), nullable=False)
    cost_per_unit = Column(Numeric(10, 4))  # auto-filled from latest inventory cost
