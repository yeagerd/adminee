#!/usr/bin/env python3
"""
Pub/Sub publisher for event-driven architecture
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from google.api_core import (
        exceptions as google_exceptions,  # type: ignore[import-not-found]
    )
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]

    PUBSUB_AVAILABLE = True
except Exception:
    PUBSUB_AVAILABLE = False
    from services.common.logging_config import get_logger

    logger = get_logger(__name__)
    logger.warning(
        "Google Cloud Pub/Sub not available. Install with: pip install google-cloud-pubsub"
    )

from services.common.events.base_events import EventMetadata
from services.common.events.calendar_events import CalendarEvent, CalendarEventData
from services.common.events.email_events import EmailData, EmailEvent
from services.common.logging_config import get_logger

logger = get_logger(__name__)


class PubSubPublisher:
    """Publishes events to Google Cloud Pub/Sub for event-driven architecture"""

    def __init__(
        self, project_id: str = "briefly-dev", emulator_host: str = "localhost:8085"
    ):
        self.project_id = project_id
        self.emulator_host = emulator_host
        self.publisher = None
        # New data-type focused topic names
        self.topics = {
            "emails": "emails",
            "calendars": "calendars",
            "word_documents": "word_documents",
            "sheet_documents": "sheet_documents",
            "presentation_documents": "presentation_documents",
            "task_documents": "task_documents",
            "todos": "todos",
            "llm_chats": "llm_chats",
            "shipment_events": "shipment_events",
            "meeting_polls": "meeting_polls",
            "bookings": "bookings",
        }

        if PUBSUB_AVAILABLE:
            self._initialize_publisher()

    def _initialize_publisher(self) -> None:
        """Initialize the Pub/Sub publisher client"""
        try:
            # Use emulator if specified
            if self.emulator_host:
                os.environ["PUBSUB_EMULATOR_HOST"] = self.emulator_host
                logger.info(f"Using Pub/Sub emulator at {self.emulator_host}")

            self.publisher = pubsub_v1.PublisherClient()
            logger.info("Pub/Sub publisher initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub publisher: {e}")
            self.publisher = None

    def _create_event_metadata(
        self,
        source_service: str = "office-service",
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> EventMetadata:
        """Create event metadata with proper tracing and context"""
        return EventMetadata(
            source_service=source_service,
            user_id=user_id,
            correlation_id=correlation_id,
            trace_id=None,
            span_id=None,
            parent_span_id=None,
            request_id=None,
            tags={"publisher": "office-service"},
        )

    async def publish_email_event(
        self,
        email_data: EmailData,
        operation: str = "create",
        batch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Publish an EmailEvent to Pub/Sub"""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available")
            return False

        try:
            # Create event metadata
            metadata = self._create_event_metadata(
                source_service="office-service",
                user_id=user_id,
                correlation_id=correlation_id,
            )

            # Validate required user_id parameter
            if not user_id:
                logger.error(
                    f"user_id is required for publishing EmailEvent {email_data.id}"
                )
                return False

            # Create EmailEvent
            email_event = EmailEvent(
                metadata=metadata,
                user_id=user_id,  # user_id is required, no fallback
                email=email_data,
                operation=operation,
                batch_id=batch_id,
                last_updated=datetime.now(timezone.utc),
                sync_timestamp=datetime.now(timezone.utc),
                provider=email_data.provider,
                sync_type="sync",
            )

            # Convert to JSON
            message_data = email_event.model_dump_json().encode("utf-8")

            # Publish to emails topic
            future = self.publisher.publish(
                f"projects/{self.project_id}/topics/{self.topics['emails']}",
                message_data,
            )
            message_id = future.result()

            logger.debug(
                f"Published EmailEvent {email_data.id} (operation: {operation}) to Pub/Sub: {message_id}"
            )
            return True

        except google_exceptions.NotFound as e:
            # Topic not found - this is a fatal error that should halt the process
            logger.error(
                f"FATAL: Pub/Sub topic '{self.topics['emails']}' not found. Halting email publishing. Error: {e}"
            )
            # Set publisher to None to prevent further attempts
            self.publisher = None
            raise RuntimeError(
                f"Pub/Sub topic '{self.topics['emails']}' not found. Please create the topic first."
            ) from e
        except Exception as e:
            logger.error(f"Failed to publish EmailEvent to Pub/Sub: {e}")
            return False

    async def publish_calendar_event(
        self,
        calendar_data: CalendarEventData,
        operation: str = "create",
        batch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> bool:
        """Publish a CalendarEvent to Pub/Sub"""
        if not self.publisher:
            logger.warning("Pub/Sub publisher not available")
            return False

        try:
            # Create event metadata
            metadata = self._create_event_metadata(
                source_service="office-service",
                user_id=user_id,
                correlation_id=correlation_id,
            )

            # Validate required user_id parameter
            if not user_id:
                logger.error(
                    f"user_id is required for publishing CalendarEvent {calendar_data.id}"
                )
                return False

            # Create CalendarEvent
            calendar_event = CalendarEvent(
                metadata=metadata,
                user_id=user_id,  # user_id is required, no fallback
                event=calendar_data,
                operation=operation,
                batch_id=batch_id,
                last_updated=datetime.now(timezone.utc),
                sync_timestamp=datetime.now(timezone.utc),
                provider=calendar_data.provider,
                calendar_id=calendar_data.calendar_id,
            )

            # Convert to JSON
            message_data = calendar_event.model_dump_json().encode("utf-8")

            # Publish to calendars topic
            future = self.publisher.publish(
                f"projects/{self.project_id}/topics/{self.topics['calendars']}",
                message_data,
            )
            message_id = future.result()

            logger.debug(
                f"Published CalendarEvent {calendar_data.id} (operation: {operation}) to Pub/Sub: {message_id}"
            )
            return True

        except google_exceptions.NotFound as e:
            # Topic not found - this is a fatal error that should halt the process
            logger.error(
                f"FATAL: Pub/Sub topic '{self.topics['calendars']}' not found. Halting calendar publishing. Error: {e}"
            )
            # Set publisher to None to prevent further attempts
            self.publisher = None
            raise RuntimeError(
                f"Pub/Sub topic '{self.topics['calendars']}' not found. Please create the topic first."
            ) from e
        except Exception as e:
            logger.error(f"Failed to publish CalendarEvent to Pub/Sub: {e}")
            return False

    async def publish_batch_emails(
        self,
        emails: List[EmailData],
        operation: str = "create",
        batch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[bool]:
        """Publish multiple EmailEvents in batch"""
        try:
            results = []

            for email in emails:
                try:
                    success = await self.publish_email_event(
                        email, operation, batch_id, user_id, correlation_id
                    )
                    results.append(success)
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the batch
                    logger.error(f"Fatal error in batch email publishing: {e}")
                    # Return partial results and re-raise the fatal error
                    return results
                except Exception as e:
                    logger.error(f"Failed to publish email in batch: {e}")
                    # Continue with other emails
                    results.append(False)
                    continue

            success_count = sum(results)
            logger.info(
                f"Published {success_count} out of {len(emails)} EmailEvents to topic {self.topics['emails']}"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to publish batch emails: {e}")
            raise

    async def publish_batch_calendar_events(
        self,
        events: List[CalendarEventData],
        operation: str = "create",
        batch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[bool]:
        """Publish multiple CalendarEvents in batch"""
        try:
            results = []

            for event in events:
                try:
                    success = await self.publish_calendar_event(
                        event, operation, batch_id, user_id, correlation_id
                    )
                    results.append(success)
                except RuntimeError as e:
                    # Fatal error (e.g., topic not found) - halt the batch
                    logger.error(f"Fatal error in batch calendar publishing: {e}")
                    # Return partial results and re-raise the fatal error
                    return results
                except Exception as e:
                    logger.error(f"Failed to publish calendar event in batch: {e}")
                    # Continue with other events
                    results.append(False)
                    continue

            success_count = sum(results)
            logger.info(
                f"Published {success_count} out of {len(events)} CalendarEvents to topic {self.topics['calendars']}"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to publish batch calendar events: {e}")
            raise

    def set_topics(
        self,
        email_topic: Optional[str] = None,
        calendar_topic: Optional[str] = None,
    ) -> None:
        """Set custom topic names"""
        if email_topic:
            self.topics["emails"] = email_topic
        if calendar_topic:
            self.topics["calendars"] = calendar_topic

        logger.info(
            f"Set topics: email={self.topics['emails']}, calendar={self.topics['calendars']}"
        )

    async def close(self) -> None:
        """Close the pubsub client"""
        try:
            if self.publisher:
                self.publisher.transport.close()  # type: ignore[attr-defined]
        except Exception:
            pass
        logger.info("PubSub publisher closed")
