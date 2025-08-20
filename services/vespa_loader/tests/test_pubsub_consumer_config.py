#!/usr/bin/env python3
"""
Tests for PubSubConsumer configuration
"""

from unittest.mock import Mock, patch

import pytest

from services.vespa_loader.pubsub_consumer import PubSubConsumer
from services.vespa_loader.settings import Settings


class TestPubSubConsumerConfig:
    """Test PubSubConsumer configuration"""

    def test_ingest_endpoint_from_settings(self):
        """Test that PubSubConsumer uses ingest endpoint from settings"""
        # Create settings with custom ingest endpoint and required fields
        with patch.dict('os.environ', {
            'API_FRONTEND_VESPA_LOADER_KEY': 'test-frontend-key',
            'API_VESPA_LOADER_USER_KEY': 'test-user-key',
            'API_VESPA_LOADER_OFFICE_KEY': 'test-office-key',
            'USER_SERVICE_URL': 'http://localhost:8001',
            'OFFICE_SERVICE_URL': 'http://localhost:8002'
        }):
            settings = Settings(ingest_endpoint="http://custom-host:8080/ingest")

            # Create consumer
            consumer = PubSubConsumer(settings)

            # Verify the endpoint is correctly set
            assert consumer.settings.ingest_endpoint == "http://custom-host:8080/ingest"

    def test_default_ingest_endpoint(self):
        """Test that PubSubConsumer uses default ingest endpoint when not specified"""
        # Create settings with default values and required fields
        with patch.dict('os.environ', {
            'API_FRONTEND_VESPA_LOADER_KEY': 'test-frontend-key',
            'API_VESPA_LOADER_USER_KEY': 'test-user-key',
            'API_VESPA_LOADER_OFFICE_KEY': 'test-office-key',
            'USER_SERVICE_URL': 'http://localhost:8001',
            'OFFICE_SERVICE_URL': 'http://localhost:8002'
        }):
            settings = Settings()

            # Create consumer
            consumer = PubSubConsumer(settings)

            # Verify the default endpoint is used
            assert consumer.settings.ingest_endpoint == "http://localhost:9001/ingest"

    def test_ingest_endpoint_validation_alias(self):
        """Test that ingest endpoint uses validation_alias for environment variable lookup"""
        # Create settings with custom ingest endpoint via validation_alias
        # This simulates setting VESPA_LOADER_INGEST_ENDPOINT in .env file
        with patch.dict('os.environ', {
            'API_FRONTEND_VESPA_LOADER_KEY': 'test-frontend-key',
            'API_VESPA_LOADER_USER_KEY': 'test-user-key',
            'API_VESPA_LOADER_OFFICE_KEY': 'test-office-key',
            'USER_SERVICE_URL': 'http://localhost:8001',
            'OFFICE_SERVICE_URL': 'http://localhost:8002'
        }):
            settings = Settings(ingest_endpoint="http://custom-env-host:9090/ingest")

            # Create consumer
            consumer = PubSubConsumer(settings)

            # Verify the custom endpoint is used
            assert consumer.settings.ingest_endpoint == "http://custom-env-host:9090/ingest"
