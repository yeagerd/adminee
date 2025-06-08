import os

import pytest
import sqlalchemy

from services.chat_service.history_manager import metadata


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

    # Recreate engine and metadata for in-memory DB
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    metadata.create_all(engine)

    yield

    # Restore original DATABASE_URL after tests
    if original_database_url is not None:
        os.environ["DATABASE_URL"] = original_database_url
    else:
        del os.environ["DATABASE_URL"]
