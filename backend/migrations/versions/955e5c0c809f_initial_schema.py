"""initial schema

Revision ID: 955e5c0c809f
Revises:
Create Date: 2026-08-11 23:31:16.125655

Creates merchants, locations, waste_events, recipes, and recipe_ingredients
tables — matching the SQLAlchemy models exactly.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "955e5c0c809f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchants",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("square_merchant_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=False),
        sa.Column("token_expires_at", sa.DateTime, nullable=False),
        sa.Column("business_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("stripe_customer_id", sa.String(64)),
        sa.Column("subscription_status", sa.String(32), server_default="trialing"),
        sa.Column("trial_ends_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("merchant_id", sa.Integer, nullable=False, index=True),
        sa.Column("square_location_id", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text),
        sa.Column("timezone", sa.String(64)),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
    )

    op.create_table(
        "waste_events",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("merchant_id", sa.Integer, nullable=False, index=True),
        sa.Column("location_id", sa.Integer, nullable=False, index=True),
        sa.Column("square_catalog_object_id", sa.String(64), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("variation_name", sa.String(255)),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(32), server_default="each"),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(10, 4)),
        sa.Column("total_cost", sa.Numeric(10, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("recorded_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("merchant_id", sa.Integer, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("selling_price", sa.Numeric(10, 2)),
        sa.Column("portions", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipes.id"), nullable=False, index=True),
        sa.Column("square_catalog_object_id", sa.String(64), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 4), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(10, 4)),
    )


def downgrade() -> None:
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("waste_events")
    op.drop_table("locations")
    op.drop_table("merchants")
