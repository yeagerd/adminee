import os
import tempfile

import databases
import pytest
import pytest_asyncio
import sqlalchemy

from services.chat_service import history_manager as hm


@pytest.fixture(autouse=True)
def force_fake_llm_globally(monkeypatch):
    """
    Global fixture to force the use of FakeLLM by clearing all LLM provider API keys.

    This ensures that ALL tests use FakeLLM instead of making real API calls,
    which makes tests faster, more reliable, and prevents accidental charges.
    """
    # Store original values for potential restoration (though tests shouldn't need real LLMs)
    original_keys = {}

    # List of common LLM provider API key environment variables
    llm_api_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "COHERE_API_KEY",
        "HUGGINGFACE_API_KEY",
        "TOGETHER_API_KEY",
        "REPLICATE_API_TOKEN",
        "MISTRAL_API_KEY",
        "PERPLEXITY_API_KEY",
        "AI21_API_KEY",
        "PALM_API_KEY",
        "BEDROCK_ACCESS_KEY_ID",
        "BEDROCK_SECRET_ACCESS_KEY",
    ]

    # Clear all LLM API keys to force FakeLLM usage
    for key in llm_api_keys:
        original_keys[key] = os.environ.get(key)
        monkeypatch.setenv(key, "")

    yield

    # Note: monkeypatch automatically restores original values on teardown


@pytest_asyncio.fixture(scope="session")
async def temp_db():
    """Create a temporary file-based SQLite database for testing."""
    # Create a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Store original values to restore later
    original_database_url = os.environ.get("DATABASE_URL")
    original_database = hm.database
    original_database_url_var = hm.DATABASE_URL

    # Set the DATABASE_URL to use the temporary file
    new_database_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = new_database_url

    # Completely reinitialize the database components
    hm.DATABASE_URL = new_database_url
    hm.database = databases.Database(new_database_url)

    # Update the database reference in all the Ormar models
    hm.Thread.ormar_config.database = hm.database
    hm.Message.ormar_config.database = hm.database
    hm.Draft.ormar_config.database = hm.database

    # Create tables and connect
    engine = sqlalchemy.create_engine(new_database_url)
    hm.metadata.create_all(engine)
    await hm.database.connect()

    yield db_path

    # Cleanup
    await hm.database.disconnect()
    hm.metadata.drop_all(engine)
    os.unlink(db_path)

    # Restore original values
    hm.DATABASE_URL = original_database_url_var
    hm.database = original_database
    hm.Thread.ormar_config.database = original_database
    hm.Message.ormar_config.database = original_database
    hm.Draft.ormar_config.database = original_database

    if original_database_url is not None:
        os.environ["DATABASE_URL"] = original_database_url
    else:
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(autouse=True)
async def clear_db(temp_db):
    """Clear data between tests."""
    try:
        await hm.Message.objects.delete(each=True)
        await hm.Draft.objects.delete(each=True)
        await hm.Thread.objects.delete(each=True)
    except Exception as e:
        # If tables don't exist yet, that's fine
        print(f"Warning: Could not clear database: {e}")
    yield
