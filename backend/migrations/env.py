"""Alembic environment configuration.

Reads DATABASE_URL from the application config so the same env var
powering the app also drives migrations — no duplicated credentials.
Uses create_engine directly (not engine_from_config) because database
URLs often contain '%' characters that configparser would try to
interpolate.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

from app.config import settings
from app.database import Base

# Autogenerate scans every model registered on Base.metadata — import them all
# so Alembic discovers the full schema.
import app.models.merchant  # noqa: F401
import app.models.waste     # noqa: F401
import app.models.recipe    # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    By skipping the Engine creation we don't even need a DBAPI to be
    available. Calls to context.execute() here emit the given string
    to the script output.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
