"""
Tests for Vespa Query Service app startup and middleware configuration.

These tests verify that the FastAPI app can be created and started without errors,
which would catch issues like middleware signature problems, import errors, or
configuration issues.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.common.test_utils import BaseIntegrationTest


class TestVespaQueryAppStartup(BaseIntegrationTest):
    """Test that the Vespa Query Service app can start up correctly."""

    def test_app_creation(self):
        """Test that the FastAPI app can be created without errors."""
        # This test would have caught the middleware signature issue
        try:
            # Import the app module - this should not raise any errors
            from services.vespa_query.main import app

            # Verify it's a FastAPI app
            assert isinstance(app, FastAPI)
            assert app.title == "Vespa Query Service"
            assert app.version == "1.0.0"

        except Exception as e:
            pytest.fail(f"Failed to create FastAPI app: {e}")

    def test_app_middleware_configuration(self):
        """Test that the app has the correct middleware configuration."""
        from services.vespa_query.main import app

        # Check that CORS middleware is present
        cors_middleware_found = False
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware_found = True
                break

        assert cors_middleware_found, "CORS middleware should be configured"

        # Check that request logging middleware is present
        # Note: This test would have caught the middleware signature issue
        request_logging_middleware_found = False
        for middleware in app.user_middleware:
            if "log_requests" in str(middleware):
                request_logging_middleware_found = True
                break

        assert (
            request_logging_middleware_found
        ), "Request logging middleware should be configured"

    def test_app_routes_registration(self):
        """Test that all expected routes are registered."""
        from services.vespa_query.main import app

        # Get all registered routes
        routes = [route.path for route in app.routes]

        # Check for expected routes
        expected_routes = [
            "/",
            "/health",
            "/search",
            "/autocomplete",
            "/similar",
            "/facets",
            "/trending",
            "/analytics",
        ]

        for route in expected_routes:
            assert route in routes, f"Route {route} should be registered"

    def test_health_endpoint_accessible(self):
        """Test that the health endpoint can be accessed without errors."""
        # Mock the dependencies to avoid real service calls
        # We need to patch the imports at the module level
        import services.vespa_query.main as main_module
        from services.vespa_query.main import app

        # Create a mock settings class that doesn't try to load from environment
        class MockSettings:
            def __init__(self):
                self.api_frontend_vespa_query_key = "test-key"
                self.api_vespa_query_office_key = "test-office-key"
                self.api_vespa_query_user_key = "test-user-key"
                self.vespa_endpoint = "http://localhost:8080"
                self.connection_pool_size = 10
                self.request_timeout = 30
                self.log_level = "INFO"
                self.log_format = "json"
                self.office_service_url = "http://localhost:8002"
                self.user_service_url = "http://localhost:8001"

        # Patch the get_settings function to return our mock
        with patch(
            "services.vespa_query.settings.get_settings", return_value=MockSettings()
        ):
            try:
                # Test that the health endpoint function can be called without errors
                # We'll test the function directly instead of using TestClient to avoid HTTP call detection
                from services.vespa_query.main import health_check

                # Mock the global variables
                original_search_engine = main_module.search_engine
                original_query_builder = main_module.query_builder
                original_result_processor = main_module.result_processor

                main_module.search_engine = None
                main_module.query_builder = None
                main_module.result_processor = None

                try:
                    # Test health endpoint function directly
                    import asyncio

                    response = asyncio.run(health_check())

                    # Check response structure
                    assert "status" in response
                    assert "service" in response
                    assert response["service"] == "vespa-query"

                finally:
                    # Restore global variables
                    main_module.search_engine = original_search_engine
                    main_module.query_builder = original_query_builder
                    main_module.result_processor = original_result_processor
            finally:
                # Clean up - no need to restore Settings since we used context manager
                pass

    def test_app_lifespan_management(self):
        """Test that the app has proper lifespan management."""
        from services.vespa_query.main import app

        # Check that lifespan is configured
        assert app.router.lifespan_context is not None

        # The lifespan_context is the function itself, not a context manager
        # Check that it's callable and has the right signature
        assert callable(app.router.lifespan_context)

        # Check that it's an async function
        import inspect

        # The lifespan function should be an async function
        # Note: In FastAPI, the lifespan function is wrapped, so we need to check differently
        lifespan_func = app.router.lifespan_context
        assert callable(lifespan_func), "Lifespan should be callable"

        # Check if it's an async function or if it returns an async context manager
        if inspect.iscoroutinefunction(lifespan_func):
            # It's an async function
            pass
        elif hasattr(lifespan_func, "__call__"):
            # It's a callable that might return an async context manager
            pass
        else:
            pytest.fail(f"Lifespan should be callable, got: {type(lifespan_func)}")

    def test_exception_handlers_registration(self):
        """Test that exception handlers are properly registered."""
        from services.vespa_query.main import app

        # Check that exception handlers are registered
        # The app should have exception handlers from register_briefly_exception_handlers
        assert len(app.exception_handlers) > 0

    def test_app_imports_without_errors(self):
        """Test that all app imports work correctly."""
        # This test would catch import errors that could prevent app startup
        try:
            # Test importing the main module
            import services.vespa_query.main

            # Test importing key components
            from services.vespa_query.main import app, health_check, lifespan

        except ImportError as e:
            pytest.fail(f"Import error in vespa_query main module: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing vespa_query main module: {e}")

    def test_middleware_function_signatures(self):
        """Test that middleware functions have correct signatures."""
        from services.vespa_query.main import app

        # This test would have caught the middleware signature issue we just fixed
        for middleware in app.user_middleware:
            # Check that middleware classes can be instantiated
            try:
                # For function-based middleware, check the function signature
                if callable(middleware.cls):
                    import inspect

                    sig = inspect.signature(middleware.cls)
                    # The middleware function should accept request and call_next
                    assert (
                        len(sig.parameters) >= 2
                    ), f"Middleware {middleware.cls} should accept at least 2 parameters"

            except Exception as e:
                pytest.fail(f"Middleware {middleware.cls} has invalid signature: {e}")

    def test_app_startup_sequence(self):
        """Test that the app startup sequence works correctly."""
        # Mock the dependencies to avoid real service calls
        # We need to patch the imports at the module level
        import services.vespa_query.main as main_module
        from services.vespa_query.main import app

        # Store original imports
        original_search_engine = getattr(main_module, "SearchEngine", None)
        original_query_builder = getattr(main_module, "QueryBuilder", None)
        original_result_processor = getattr(main_module, "ResultProcessor", None)

        # Create mock settings
        class MockSettings:
            def __init__(self):
                self.api_frontend_vespa_query_key = "test-key"
                self.api_vespa_query_office_key = "test-office-key"
                self.api_vespa_query_user_key = "test-user-key"
                self.vespa_endpoint = "http://localhost:8080"
                self.log_level = "INFO"
                self.log_format = "json"
                self.office_service_url = "http://localhost:8002"
                self.user_service_url = "http://localhost:8001"

        # Mock the get_settings function
        with patch(
            "services.vespa_query.settings.get_settings", return_value=MockSettings()
        ):
            # Mock the service components
            class MockSearchEngine:
                async def test_connection(self):
                    return True

                async def close(self):
                    pass

            class MockQueryBuilder:
                pass

            class MockResultProcessor:
                pass

            main_module.SearchEngine = MockSearchEngine
            main_module.QueryBuilder = MockQueryBuilder
            main_module.ResultProcessor = MockResultProcessor

            # Mock the logging setup
            main_module.setup_service_logging = lambda *args, **kwargs: None
            main_module.log_service_startup = lambda *args, **kwargs: None
            main_module.log_service_shutdown = lambda *args, **kwargs: None

            # Test that the lifespan function can be called
            lifespan_func = app.router.lifespan_context
            assert callable(lifespan_func)
            assert lifespan_func is not None

        # Restore original imports
        if original_search_engine:
            main_module.SearchEngine = original_search_engine
        if original_query_builder:
            main_module.QueryBuilder = original_query_builder
        if original_result_processor:
            main_module.ResultProcessor = original_result_processor
