"""
Database configuration for User Management Service.

Sets up database connection using Ormar ORM and SQLAlchemy.
"""

import databases
import ormar
import sqlalchemy

from .settings import settings

# Database and metadata setup
database = databases.Database(settings.database_url)
metadata = sqlalchemy.MetaData()

# Base OrmarConfig for all models
base_ormar_config = ormar.OrmarConfig(database=database, metadata=metadata)


# Database lifecycle management
async def connect_database():
    """Connect to the database."""
    if not database.is_connected:
        await database.connect()


async def disconnect_database():
    """Disconnect from the database."""
    if database.is_connected:
        await database.disconnect()


# Create all tables (for development/testing)
async def create_all_tables():
    """Create all database tables. Use Alembic migrations in production."""
    engine = sqlalchemy.create_engine(settings.database_url)
    metadata.create_all(engine)
