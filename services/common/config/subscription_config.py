"""
Shared subscription configuration for consistent naming across services.
"""

from typing import Dict, List


class SubscriptionConfig:
    """Configuration for subscription naming and management."""

    # Service prefixes for subscriptions
    SERVICE_PREFIXES = {
        "vespa_loader": "vespa-loader",
        "contact_discovery": "contact-discovery",
        "meetings": "meetings",
        "shipments": "shipments",
        "chat": "chat",
        "frontend_sse": "frontend-sse",
        "email_sync": "email-sync",
        "calendar_sync": "calendar-sync",
        "document_sync": "document-sync",
        "todo_sync": "todo-sync",
    }

    # Topic names for data types
    TOPIC_NAMES = {
        "emails": "emails",
        "calendars": "calendars",
        "contacts": "contacts",
        "word_documents": "word_documents",
        "word_fragments": "word_fragments",
        "sheet_documents": "sheet_documents",
        "sheet_fragments": "sheet_fragments",
        "presentation_documents": "presentation_documents",
        "presentation_fragments": "presentation_fragments",
        "task_documents": "task_documents",
        "todos": "todos",
        "llm_chats": "llm_chats",
        "shipment_events": "shipment_events",
        "meeting_polls": "meeting_polls",
        "bookings": "bookings",
    }

    # Default subscription settings
    DEFAULT_SUBSCRIPTION_SETTINGS = {
        "ack_deadline_seconds": 60,
        "retain_acked_messages": False,
        "enable_exactly_once_delivery": False,
        "filter": None,
        "dead_letter_topic": None,
        "max_retry_attempts": 5,
    }

    # Service-specific subscription configurations
    SERVICE_SUBSCRIPTIONS = {
        "vespa_loader": {
            "emails": {
                "subscription_name": "vespa-loader-emails",
                "batch_size": 50,
                "ack_deadline_seconds": 120,
            },
            "calendars": {
                "subscription_name": "vespa-loader-calendars",
                "batch_size": 20,
                "ack_deadline_seconds": 120,
            },
            "contacts": {
                "subscription_name": "vespa-loader-contacts",
                "batch_size": 100,
                "ack_deadline_seconds": 120,
            },
            "word_documents": {
                "subscription_name": "vespa-loader-word-documents",
                "batch_size": 10,
                "ack_deadline_seconds": 180,
            },
            "word_fragments": {
                "subscription_name": "vespa-loader-word-fragments",
                "batch_size": 20,
                "ack_deadline_seconds": 180,
            },
            "sheet_documents": {
                "subscription_name": "vespa-loader-sheet-documents",
                "batch_size": 10,
                "ack_deadline_seconds": 180,
            },
            "sheet_fragments": {
                "subscription_name": "vespa-loader-sheet-fragments",
                "batch_size": 20,
                "ack_deadline_seconds": 180,
            },
            "presentation_documents": {
                "subscription_name": "vespa-loader-presentation-documents",
                "batch_size": 10,
                "ack_deadline_seconds": 180,
            },
            "presentation_fragments": {
                "subscription_name": "vespa-loader-presentation-fragments",
                "batch_size": 20,
                "ack_deadline_seconds": 180,
            },
            "task_documents": {
                "subscription_name": "vespa-loader-task-documents",
                "batch_size": 10,
                "ack_deadline_seconds": 180,
            },
            "todos": {
                "subscription_name": "vespa-loader-todos",
                "batch_size": 50,
                "ack_deadline_seconds": 120,
            },
            "llm_chats": {
                "subscription_name": "vespa-loader-llm-chats",
                "batch_size": 25,
                "ack_deadline_seconds": 120,
            },
            "shipment_events": {
                "subscription_name": "vespa-loader-shipment-events",
                "batch_size": 30,
                "ack_deadline_seconds": 120,
            },
            "meeting_polls": {
                "subscription_name": "vespa-loader-meeting-polls",
                "batch_size": 20,
                "ack_deadline_seconds": 120,
            },
            "bookings": {
                "subscription_name": "vespa-loader-bookings",
                "batch_size": 40,
                "ack_deadline_seconds": 120,
            },
        },
        "contact_discovery": {
            "emails": {
                "subscription_name": "contact-discovery-emails",
                "batch_size": 100,
                "ack_deadline_seconds": 60,
            },
            "calendars": {
                "subscription_name": "contact-discovery-calendars",
                "batch_size": 50,
                "ack_deadline_seconds": 60,
            },
            "contacts": {
                "subscription_name": "contact-discovery-contacts",
                "batch_size": 100,
                "ack_deadline_seconds": 60,
            },
            "word_documents": {
                "subscription_name": "contact-discovery-word-documents",
                "batch_size": 25,
                "ack_deadline_seconds": 60,
            },
            "sheet_documents": {
                "subscription_name": "contact-discovery-sheet-documents",
                "batch_size": 25,
                "ack_deadline_seconds": 60,
            },
            "presentation_documents": {
                "subscription_name": "contact-discovery-presentation-documents",
                "batch_size": 25,
                "ack_deadline_seconds": 60,
            },
            "todos": {
                "subscription_name": "contact-discovery-todos",
                "batch_size": 100,
                "ack_deadline_seconds": 60,
            },
        },
        "meetings": {
            "calendars": {
                "subscription_name": "meetings-calendars",
                "batch_size": 20,
                "ack_deadline_seconds": 60,
            },
        },
        "shipments": {
            "emails": {
                "subscription_name": "shipments-emails",
                "batch_size": 50,
                "ack_deadline_seconds": 60,
            },
        },
        "frontend_sse": {
            "emails": {
                "subscription_name": "frontend-sse-emails",
                "batch_size": 10,
                "ack_deadline_seconds": 30,
            },
            "calendars": {
                "subscription_name": "frontend-sse-calendars",
                "batch_size": 10,
                "ack_deadline_seconds": 30,
            },
            "contacts": {
                "subscription_name": "frontend-sse-contacts",
                "batch_size": 10,
                "ack_deadline_seconds": 30,
            },
            "todos": {
                "subscription_name": "frontend-sse-todos",
                "batch_size": 10,
                "ack_deadline_seconds": 30,
            },
        },
    }

    @classmethod
    def get_subscription_name(cls, service_name: str, topic_name: str) -> str:
        """Get the subscription name for a service and topic."""
        if service_name in cls.SERVICE_SUBSCRIPTIONS:
            if topic_name in cls.SERVICE_SUBSCRIPTIONS[service_name]:
                return cls.SERVICE_SUBSCRIPTIONS[service_name][topic_name][
                    "subscription_name"
                ]

        # Fallback to default naming convention
        service_prefix = cls.SERVICE_PREFIXES.get(service_name, service_name)
        return f"{service_prefix}-{topic_name}"

    @classmethod
    def get_subscription_config(
        cls, service_name: str, topic_name: str
    ) -> Dict[str, any]:
        """Get the complete subscription configuration for a service and topic."""
        config = cls.DEFAULT_SUBSCRIPTION_SETTINGS.copy()

        if service_name in cls.SERVICE_SUBSCRIPTIONS:
            if topic_name in cls.SERVICE_SUBSCRIPTIONS[service_name]:
                config.update(cls.SERVICE_SUBSCRIPTIONS[service_name][topic_name])

        return config

    @classmethod
    def get_service_topics(cls, service_name: str) -> List[str]:
        """Get the list of topics that a service should subscribe to."""
        if service_name in cls.SERVICE_SUBSCRIPTIONS:
            return list(cls.SERVICE_SUBSCRIPTIONS[service_name].keys())
        return []

    @classmethod
    def get_topic_subscribers(cls, topic_name: str) -> List[str]:
        """Get the list of services that subscribe to a specific topic."""
        subscribers = []
        for service_name, topics in cls.SERVICE_SUBSCRIPTIONS.items():
            if topic_name in topics:
                subscribers.append(service_name)
        return subscribers

    @classmethod
    def validate_subscription_config(cls, service_name: str, topic_name: str) -> bool:
        """Validate that a service is configured to subscribe to a topic."""
        return (
            service_name in cls.SERVICE_SUBSCRIPTIONS
            and topic_name in cls.SERVICE_SUBSCRIPTIONS[service_name]
        )

    @classmethod
    def get_all_subscriptions(cls) -> Dict[str, Dict[str, Dict[str, any]]]:
        """Get all subscription configurations."""
        return cls.SERVICE_SUBSCRIPTIONS.copy()

    @classmethod
    def get_subscription_stats(cls) -> Dict[str, any]:
        """Get statistics about subscription configurations."""
        total_services = len(cls.SERVICE_SUBSCRIPTIONS)
        total_subscriptions = sum(
            len(topics) for topics in cls.SERVICE_SUBSCRIPTIONS.values()
        )

        topic_usage = {}
        for service_name, topics in cls.SERVICE_SUBSCRIPTIONS.items():
            for topic_name in topics:
                if topic_name not in topic_usage:
                    topic_usage[topic_name] = []
                topic_usage[topic_name].append(service_name)

        return {
            "total_services": total_services,
            "total_subscriptions": total_subscriptions,
            "topic_usage": topic_usage,
            "service_coverage": {
                service: len(topics)
                for service, topics in cls.SERVICE_SUBSCRIPTIONS.items()
            },
        }
