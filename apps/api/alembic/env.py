"""
Alembic Environment Configuration
"""

from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection

from alembic import context

# Import your models and Base
from app.db.session import Base
from app.models import (
    User, Project, Scenario, SimulationRun, AgentResponse,
    DataSource, CensusData, RegionalProfile, ValidationResult,
    PersonaTemplate, PersonaRecord, PersonaUpload, AIResearchJob,
    Product, ProductRun, AgentInteraction, ProductResult, Benchmark, ValidationRecord
)
from app.core.config import settings

# this is the Alembic Config object
config = context.config

# Set the database URL from settings (use sync driver for migrations)
# Replace asyncpg with psycopg2 and ensure localhost resolves to 127.0.0.1
sync_database_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("localhost", "127.0.0.1")
# Note: We use the URL directly in run_migrations_online() instead of set_main_option
# to avoid ConfigParser's % interpolation issues with URL-encoded passwords

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use sync_database_url directly instead of config.get_main_option
    # to avoid ConfigParser's % interpolation issues
    context.configure(
        url=sync_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        sync_database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
