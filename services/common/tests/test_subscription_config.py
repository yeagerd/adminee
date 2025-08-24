"""
Tests for the subscription configuration.
"""

from services.common.config.subscription_config import SubscriptionConfig


class TestSubscriptionConfig:
    """Test cases for SubscriptionConfig."""

    def test_get_subscription_name(self):
        """Test getting subscription names for different services and topics."""
        # Test vespa_loader service
        assert (
            SubscriptionConfig.get_subscription_name("vespa_loader", "emails")
            == "vespa-loader-emails"
        )
        assert (
            SubscriptionConfig.get_subscription_name("vespa_loader", "calendars")
            == "vespa-loader-calendars"
        )
        assert (
            SubscriptionConfig.get_subscription_name("vespa_loader", "contacts")
            == "vespa-loader-contacts"
        )

        # Test contact_discovery service
        assert (
            SubscriptionConfig.get_subscription_name("contact_discovery", "emails")
            == "contact-discovery-emails"
        )
        assert (
            SubscriptionConfig.get_subscription_name("contact_discovery", "calendars")
            == "contact-discovery-calendars"
        )

        # Test meetings service
        assert (
            SubscriptionConfig.get_subscription_name("meetings", "calendars")
            == "meetings-calendars"
        )

        # Test shipments service
        assert (
            SubscriptionConfig.get_subscription_name("shipments", "emails")
            == "shipments-emails"
        )

        # Test frontend_sse service
        assert (
            SubscriptionConfig.get_subscription_name("frontend_sse", "emails")
            == "frontend-sse-emails"
        )
        assert (
            SubscriptionConfig.get_subscription_name("frontend_sse", "todos")
            == "frontend-sse-todos"
        )

        # Test fallback for unknown service
        assert (
            SubscriptionConfig.get_subscription_name("unknown_service", "emails")
            == "unknown_service-emails"
        )

    def test_get_subscription_config(self):
        """Test getting complete subscription configurations."""
        # Test vespa_loader emails
        config = SubscriptionConfig.get_subscription_config("vespa_loader", "emails")
        assert config["subscription_name"] == "vespa-loader-emails"
        assert config["batch_size"] == 50
        assert config["ack_deadline_seconds"] == 120
        assert config["retain_acked_messages"] is False

        # Test contact_discovery emails
        config = SubscriptionConfig.get_subscription_config(
            "contact_discovery", "emails"
        )
        assert config["subscription_name"] == "contact-discovery-emails"
        assert config["batch_size"] == 100
        assert config["ack_deadline_seconds"] == 60

        # Test default values for unknown service/topic
        config = SubscriptionConfig.get_subscription_config(
            "unknown_service", "unknown_topic"
        )
        assert config["ack_deadline_seconds"] == 60
        assert config["retain_acked_messages"] is False
        assert config["enable_exactly_once_delivery"] is False

    def test_get_service_topics(self):
        """Test getting topics for different services."""
        # Test vespa_loader service
        vespa_topics = SubscriptionConfig.get_service_topics("vespa_loader")
        assert "emails" in vespa_topics
        assert "calendars" in vespa_topics
        assert "word_documents" in vespa_topics
        assert "sheet_documents" in vespa_topics
        assert "presentation_documents" in vespa_topics
        assert "task_documents" in vespa_topics
        assert "todos" in vespa_topics
        assert "llm_chats" in vespa_topics
        assert "shipment_events" in vespa_topics
        assert "meeting_polls" in vespa_topics
        assert "bookings" in vespa_topics

        # Test contact_discovery service
        contact_topics = SubscriptionConfig.get_service_topics("contact_discovery")
        assert "emails" in contact_topics
        assert "calendars" in contact_topics
        assert "word_documents" in contact_topics
        assert "sheet_documents" in contact_topics
        assert "presentation_documents" in contact_topics
        assert "todos" in contact_topics

        # Test frontend_sse service
        frontend_topics = SubscriptionConfig.get_service_topics("frontend_sse")
        assert "emails" in frontend_topics
        assert "calendars" in frontend_topics
        assert "todos" in frontend_topics

    def test_get_topic_subscribers(self):
        """Test getting subscribers for different topics."""
        # Test emails topic
        email_subscribers = SubscriptionConfig.get_topic_subscribers("emails")
        assert "vespa_loader" in email_subscribers
        assert "contact_discovery" in email_subscribers
        assert "shipments" in email_subscribers
        assert "frontend_sse" in email_subscribers

        # Test calendars topic
        calendar_subscribers = SubscriptionConfig.get_topic_subscribers("calendars")
        assert "vespa_loader" in calendar_subscribers
        assert "contact_discovery" in calendar_subscribers
        assert "meetings" in calendar_subscribers
        assert "frontend_sse" in calendar_subscribers

        # Test word_documents topic
        word_doc_subscribers = SubscriptionConfig.get_topic_subscribers(
            "word_documents"
        )
        assert "vespa_loader" in word_doc_subscribers
        assert "contact_discovery" in word_doc_subscribers

        # Test unknown topic
        unknown_subscribers = SubscriptionConfig.get_topic_subscribers("unknown_topic")
        assert len(unknown_subscribers) == 0

    def test_validate_subscription_config(self):
        """Test subscription configuration validation."""
        # Test valid configurations
        assert (
            SubscriptionConfig.validate_subscription_config("vespa_loader", "emails")
            is True
        )
        assert (
            SubscriptionConfig.validate_subscription_config(
                "contact_discovery", "calendars"
            )
            is True
        )
        assert (
            SubscriptionConfig.validate_subscription_config("meetings", "calendars")
            is True
        )
        assert (
            SubscriptionConfig.validate_subscription_config("shipments", "emails")
            is True
        )
        assert (
            SubscriptionConfig.validate_subscription_config("frontend_sse", "todos")
            is True
        )

        # Test invalid configurations
        assert (
            SubscriptionConfig.validate_subscription_config("unknown_service", "emails")
            is False
        )
        assert (
            SubscriptionConfig.validate_subscription_config(
                "vespa_loader", "unknown_topic"
            )
            is False
        )
        assert (
            SubscriptionConfig.validate_subscription_config(
                "unknown_service", "unknown_topic"
            )
            is False
        )

    def test_get_all_subscriptions(self):
        """Test getting all subscription configurations."""
        all_subscriptions = SubscriptionConfig.get_all_subscriptions()

        # Check that all expected services are present
        assert "vespa_loader" in all_subscriptions
        assert "contact_discovery" in all_subscriptions
        assert "meetings" in all_subscriptions
        assert "shipments" in all_subscriptions
        assert "frontend_sse" in all_subscriptions

        # Check vespa_loader has all expected topics
        vespa_subscriptions = all_subscriptions["vespa_loader"]
        assert "emails" in vespa_subscriptions
        assert "calendars" in vespa_subscriptions
        assert "contacts" in vespa_subscriptions
        assert "word_documents" in vespa_subscriptions
        assert "sheet_documents" in vespa_subscriptions
        assert "presentation_documents" in vespa_subscriptions
        assert "task_documents" in vespa_subscriptions
        assert "todos" in vespa_subscriptions
        assert "llm_chats" in vespa_subscriptions
        assert "shipment_events" in vespa_subscriptions
        assert "meeting_polls" in vespa_subscriptions
        assert "bookings" in vespa_subscriptions

        # Check contact_discovery has expected topics
        contact_subscriptions = all_subscriptions["contact_discovery"]
        assert "emails" in contact_subscriptions
        assert "calendars" in contact_subscriptions
        assert "word_documents" in contact_subscriptions
        assert "sheet_documents" in contact_subscriptions
        assert "presentation_documents" in contact_subscriptions
        assert "todos" in contact_subscriptions

    def test_get_subscription_stats(self):
        """Test getting subscription statistics."""
        stats = SubscriptionConfig.get_subscription_stats()

        # Check basic stats
        assert stats["total_services"] > 0
        assert stats["total_subscriptions"] > 0

        # Check service coverage
        service_coverage = stats["service_coverage"]
        assert "vespa_loader" in service_coverage
        assert "contact_discovery" in service_coverage
        assert "meetings" in service_coverage
        assert "shipments" in service_coverage
        assert "frontend_sse" in service_coverage

        # Check topic usage
        topic_usage = stats["topic_usage"]
        assert "emails" in topic_usage
        assert "calendars" in topic_usage
        assert "word_documents" in topic_usage
        assert "todos" in topic_usage

        # Verify specific topic subscribers
        assert "vespa_loader" in topic_usage["emails"]
        assert "contact_discovery" in topic_usage["emails"]
        assert "shipments" in topic_usage["emails"]
        assert "frontend_sse" in topic_usage["emails"]

    def test_topic_names_consistency(self):
        """Test that topic names are consistent across the configuration."""
        topic_names = SubscriptionConfig.TOPIC_NAMES

        # Check that all expected topic names are present
        assert "emails" in topic_names
        assert "calendars" in topic_names
        assert "contacts" in topic_names
        assert "word_documents" in topic_names
        assert "sheet_documents" in topic_names
        assert "presentation_documents" in topic_names
        assert "task_documents" in topic_names
        assert "todos" in topic_names
        assert "llm_chats" in topic_names
        assert "shipment_events" in topic_names
        assert "meeting_polls" in topic_names
        assert "bookings" in topic_names

        # Check that topic names match the values
        assert topic_names["emails"] == "emails"
        assert topic_names["calendars"] == "calendars"
        assert topic_names["word_documents"] == "word_documents"
        assert topic_names["todos"] == "todos"

    def test_service_prefixes_consistency(self):
        """Test that service prefixes are consistent."""
        service_prefixes = SubscriptionConfig.SERVICE_PREFIXES

        # Check that all expected service prefixes are present
        assert "vespa_loader" in service_prefixes
        assert "contact_discovery" in service_prefixes
        assert "meetings" in service_prefixes
        assert "shipments" in service_prefixes
        assert "frontend_sse" in service_prefixes

        # Check that prefixes follow the expected pattern
        assert service_prefixes["vespa_loader"] == "vespa-loader"
        assert service_prefixes["contact_discovery"] == "contact-discovery"
        assert service_prefixes["meetings"] == "meetings"
        assert service_prefixes["shipments"] == "shipments"
        assert service_prefixes["frontend_sse"] == "frontend-sse"

    def test_default_subscription_settings(self):
        """Test that default subscription settings are properly configured."""
        default_settings = SubscriptionConfig.DEFAULT_SUBSCRIPTION_SETTINGS

        # Check that all expected settings are present
        assert "ack_deadline_seconds" in default_settings
        assert "retain_acked_messages" in default_settings
        assert "enable_exactly_once_delivery" in default_settings
        assert "filter" in default_settings
        assert "dead_letter_topic" in default_settings
        assert "max_retry_attempts" in default_settings

        # Check that default values are reasonable
        assert default_settings["ack_deadline_seconds"] == 60
        assert default_settings["retain_acked_messages"] is False
        assert default_settings["enable_exactly_once_delivery"] is False
        assert default_settings["filter"] is None
        assert default_settings["dead_letter_topic"] is None
        assert default_settings["max_retry_attempts"] == 5
