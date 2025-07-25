from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_disposes_engine():
    with (
        patch("services.chat.main.history_manager") as mock_history_manager,
        patch("services.chat.settings.get_settings") as mock_get_settings,
    ):
        # Set up the mock settings to return valid values
        mock_settings = AsyncMock()
        mock_settings.api_frontend_chat_key = "test_key"
        mock_settings.api_chat_user_key = "test_key"
        mock_settings.api_chat_office_key = "test_key"
        mock_settings.user_management_service_url = "http://localhost:8001"
        mock_settings.office_service_url = "http://localhost:8003"
        mock_settings.log_level = "INFO"
        mock_settings.log_format = "json"
        mock_get_settings.return_value = mock_settings

        mock_engine = AsyncMock()
        mock_history_manager.init_db = AsyncMock()
        mock_history_manager.get_engine.return_value = mock_engine

        # Import lifespan after patching
        from fastapi import FastAPI

        from services.chat.main import lifespan

        app = FastAPI()
        async with lifespan(app):
            pass

        # Assert that init_db was called on startup
        mock_history_manager.init_db.assert_called_once()
        # Assert that get_engine was called
        mock_history_manager.get_engine.assert_called_once()
        # Assert that dispose was called on the engine
        mock_engine.dispose.assert_called_once()
