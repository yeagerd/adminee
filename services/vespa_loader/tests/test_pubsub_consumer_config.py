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

    def test_pubsub_consumer_instantiation(self):
        """Test that PubSubConsumer can be instantiated with required settings"""
        # Create settings with required fields
        with patch.dict(
            "os.environ",
            {
                "API_FRONTEND_VESPA_LOADER_KEY": "test-frontend-key",
                "API_VESPA_LOADER_USER_KEY": "test-user-key",
                "API_VESPA_LOADER_OFFICE_KEY": "test-office-key",
                "USER_SERVICE_URL": "http://localhost:8001",
                "OFFICE_SERVICE_URL": "http://localhost:8002",
            },
        ):
            settings = Settings()

            # Create consumer - should not raise any exceptions
            consumer = PubSubConsumer(settings)

            # Verify basic attributes are set
            assert consumer.settings == settings
            assert consumer.email_processor is not None
            assert (
                len(consumer.topics) == 3
            )  # email-backfill, calendar-updates, contact-updates
