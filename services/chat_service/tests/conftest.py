import pytest
import asyncio
from services.chat_service.history_manager import database, metadata
import sqlalchemy

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    # Create tables for in-memory SQLite before any tests run
    engine = sqlalchemy.create_engine("sqlite:///memory")
    metadata.create_all(engine)
    # Connect the Ormar database
    loop = asyncio.get_event_loop()
    loop.run_until_complete(database.connect())
    yield
    loop.run_until_complete(database.disconnect())
