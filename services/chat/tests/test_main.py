from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from services.chat.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_disposes_engine():
    """
    Test that the lifespan context manager disposes of the engine on shutdown.
    """
    mock_engine = AsyncMock()
    # Ensure that init_db is also an AsyncMock if it's awaited
    mock_history_manager = MagicMock()
    mock_history_manager.init_db = AsyncMock()  # Make init_db an awaitable mock
    mock_history_manager.get_engine.return_value = mock_engine

    # Patch history_manager and its functions used within lifespan
    with (
        patch("services.chat.main.history_manager", mock_history_manager),
        patch("services.chat.main.get_settings", MagicMock()),
    ):  # Patch get_settings to avoid SettingsNotConfiguredError
        # Create a dummy FastAPI app instance
        app = FastAPI()

        # Execute the lifespan context manager
        async with lifespan(app):
            # This block simulates the application running
            pass

    # Assert that init_db was called on startup
    mock_history_manager.init_db.assert_called_once()

    # Assert that get_engine was called
    mock_history_manager.get_engine.assert_called_once()

    # Assert that dispose was called on the engine
    mock_engine.dispose.assert_called_once()
