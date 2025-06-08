import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Insert the path to your project to allow alembic to find your modules
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from core.config import get_settings # Adjusted import
from models.models import metadata as target_metadata_models # Adjusted import

config = context.config
fileConfig(config.config_file_name)

# Use DATABASE_URL from settings
db_settings = get_settings()
config.set_main_option('sqlalchemy.url', db_settings.DATABASE_URL)

target_metadata = target_metadata_models # Use metadata from your models.py

def run_migrations_offline():
    # ... (rest of the function remains the same)
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    # ... (rest of the function remains the same)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
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
