from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from services.chat.main import lifespan


@pytest.mark.asyncio
@patch("services.chat.main.history_manager")
@patch("services.chat.main.get_settings")
async def test_lifespan_disposes_engine(mock_get_settings, mock_history_manager):
    """
    Test that the lifespan context manager disposes of the engine on shutdown.
    """
    mock_engine = AsyncMock()
    mock_history_manager.init_db = AsyncMock()
    mock_history_manager.get_engine.return_value = mock_engine

    # Execute the lifespan context manager
    app = FastAPI()
    async with lifespan(app):
        pass

    # Assert that init_db was called on startup
    mock_history_manager.init_db.assert_called_once()
    # Assert that get_engine was called
    mock_history_manager.get_engine.assert_called_once()
    # Assert that dispose was called on the engine
    mock_engine.dispose.assert_called_once()
