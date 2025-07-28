from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_disposes_engine():
    import services.chat.settings as chat_settings
    from services.chat.settings import Settings

    with patch("services.chat.main.history_manager") as mock_history_manager:
        # Set up the settings singleton to return valid values
        chat_settings._settings = Settings(
            api_frontend_chat_key="test-frontend-chat-key",
            api_chat_user_key="test-chat-user-key",
            api_chat_office_key="test-chat-office-key",
            user_service_url="http://localhost:8001",
            office_service_url="http://localhost:8003",
            log_level="INFO",
            log_format="json",
            db_url_chat="sqlite:///test.db",
            llm_provider="fake",
            llm_model="fake-model",
            max_tokens=2000,
            openai_api_key=None,
            service_name="chat-service",
            host="0.0.0.0",
            port=8000,
            debug=False,
            environment="test",
        )

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

        # Clean up singleton
        chat_settings._settings = None
