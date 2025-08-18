#!/usr/bin/env python3
"""
Core routing logic for office data distribution
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from services.office_router.models import DownstreamService, RoutingResult
from services.office_router.settings import Settings

logger = logging.getLogger(__name__)


class OfficeRouter:
    """Routes office data to multiple downstream services"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.downstream_services = self._initialize_downstream_services()
        self.session: Optional[aiohttp.ClientSession] = None

    def _initialize_downstream_services(self) -> Dict[str, DownstreamService]:
        """Initialize downstream service configurations"""
        return {
            "vespa": DownstreamService(
                name="vespa",
                endpoint=self.settings.vespa_endpoint,
                enabled=self.settings.vespa_enabled,
                timeout=self.settings.vespa_timeout,
            ),
            "shipments": DownstreamService(
                name="shipments",
                endpoint=self.settings.shipments_endpoint,
                enabled=self.settings.shipments_enabled,
                timeout=self.settings.shipments_timeout,
            ),
            "contacts": DownstreamService(
                name="contacts",
                endpoint=self.settings.contacts_endpoint,
                enabled=self.settings.contacts_enabled,
                timeout=self.settings.contacts_timeout,
            ),
            "notifications": DownstreamService(
                name="notifications",
                endpoint=self.settings.notifications_endpoint,
                enabled=self.settings.notifications_enabled,
                timeout=self.settings.notifications_timeout,
            ),
        }

    async def start(self) -> None:
        """Start the router and create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("Office Router started")

    async def stop(self) -> None:
        """Stop the router and close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Office Router stopped")

    async def route_email(self, email_data: Dict[str, Any]) -> RoutingResult:
        """Route email data to all enabled downstream services"""
        logger.info(
            f"Routing email {email_data.get('id', 'unknown')} to downstream services"
        )

        routing_tasks = []
        results: Dict[str, Any] = {}

        # Create routing tasks for each enabled service
        for service_name, service in self.downstream_services.items():
            if service.enabled:
                task = self._route_to_service(service_name, service, email_data)
                routing_tasks.append(task)

        # Execute all routing tasks concurrently
        if routing_tasks:
            service_results = await asyncio.gather(
                *routing_tasks, return_exceptions=True
            )

            # Process results
            for i, (service_name, service) in enumerate(
                self.downstream_services.items()
            ):
                if service.enabled:
                    result = service_results[i]
                    if isinstance(result, Exception):
                        logger.error(f"Failed to route to {service_name}: {result}")
                        results[service_name] = {
                            "status": "error",
                            "error": str(result),
                        }
                    else:
                        results[service_name] = result

        return RoutingResult(
            timestamp=datetime.utcnow().isoformat(),
            source_data_id=email_data.get("id"),
            results=results,
        )

    async def route_calendar(self, calendar_data: Dict[str, Any]) -> RoutingResult:
        """Route calendar data to downstream services"""
        logger.info(
            f"Routing calendar event {calendar_data.get('id', 'unknown')} to downstream services"
        )

        # For now, only route to vespa and notifications
        routing_tasks = []
        results = {}

        # Route to vespa for search indexing
        if self.downstream_services["vespa"].enabled:
            task = self._route_to_service(
                "vespa", self.downstream_services["vespa"], calendar_data
            )
            routing_tasks.append(task)

        # Route to notifications for calendar reminders
        if self.downstream_services["notifications"].enabled:
            task = self._route_to_service(
                "notifications",
                self.downstream_services["notifications"],
                calendar_data,
            )
            routing_tasks.append(task)

        # Execute routing tasks
        if routing_tasks:
            service_results = await asyncio.gather(
                *routing_tasks, return_exceptions=True
            )

            # Process results
            for i, result in enumerate(service_results):
                service_name = list(self.downstream_services.keys())[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to route calendar to {service_name}: {result}"
                    )
                    results[service_name] = {"status": "error", "error": str(result)}
                else:
                    results[service_name] = result

        return RoutingResult(
            timestamp=datetime.utcnow().isoformat(),
            source_data_id=calendar_data.get("id"),
            results=results,
        )

    async def route_contact(self, contact_data: Dict[str, Any]) -> RoutingResult:
        """Route contact data to downstream services"""
        logger.info(
            f"Routing contact {contact_data.get('id', 'unknown')} to downstream services"
        )

        # Route to vespa and contacts service
        routing_tasks = []
        results = {}

        if self.downstream_services["vespa"].enabled:
            task = self._route_to_service(
                "vespa", self.downstream_services["vespa"], contact_data
            )
            routing_tasks.append(task)

        if self.downstream_services["contacts"].enabled:
            task = self._route_to_service(
                "contacts", self.downstream_services["contacts"], contact_data
            )
            routing_tasks.append(task)

        # Execute routing tasks
        if routing_tasks:
            service_results = await asyncio.gather(
                *routing_tasks, return_exceptions=True
            )

            # Process results
            for i, result in enumerate(service_results):
                service_name = list(self.downstream_services.keys())[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to route contact to {service_name}: {result}")
                    results[service_name] = {"status": "error", "error": str(result)}
                else:
                    results[service_name] = result

        return RoutingResult(
            timestamp=datetime.utcnow().isoformat(),
            source_data_id=contact_data.get("id"),
            results=results,
        )

    async def _route_to_service(
        self, service_name: str, service: DownstreamService, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route data to a specific downstream service"""
        if not self.session:
            raise RuntimeError("Router session not initialized")

        try:
            # Prepare the data for the specific service
            service_data = self._prepare_data_for_service(service_name, data)

            # Send data to service
            async with self.session.post(
                f"{service.endpoint}/ingest",
                json=service_data,
                timeout=aiohttp.ClientTimeout(total=service.timeout),
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully routed to {service_name}")
                    return {"status": "success", "response": result}
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Service {service_name} returned {response.status}: {error_text}"
                    )
                    return {
                        "status": "error",
                        "http_status": response.status,
                        "error": error_text,
                    }

        except asyncio.TimeoutError:
            logger.error(f"Timeout routing to {service_name}")
            return {
                "status": "timeout",
                "error": f"Request to {service_name} timed out after {service.timeout}s",
            }
        except Exception as e:
            logger.error(f"Error routing to {service_name}: {e}")
            return {"status": "error", "error": str(e)}

    def _prepare_data_for_service(
        self, service_name: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare data for specific downstream service"""
        if service_name == "vespa":
            # Transform data for Vespa indexing
            return {
                "document_type": "briefly_document",
                "fields": {
                    "user_id": data.get("user_id"),
                    "doc_id": data.get("id"),
                    "provider": data.get("provider"),
                    "source_type": data.get("type", "email"),
                    "title": data.get("subject", ""),
                    "content": data.get("body", ""),
                    "search_text": data.get("body", ""),
                    "sender": data.get("from"),
                    "recipients": data.get("to", []),
                    "thread_id": data.get("thread_id"),
                    "folder": data.get("folder"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "metadata": data.get("metadata", {}),
                },
            }
        elif service_name == "shipments":
            # Extract shipment-related information
            return {
                "email_id": data.get("id"),
                "user_id": data.get("user_id"),
                "subject": data.get("subject"),
                "body": data.get("body"),
                "attachments": data.get("attachments", []),
                "timestamp": data.get("created_at"),
            }
        elif service_name == "contacts":
            # Extract contact information
            return {
                "email_id": data.get("id"),
                "user_id": data.get("user_id"),
                "sender": data.get("from"),
                "recipients": data.get("to", []),
                "subject": data.get("subject"),
                "timestamp": data.get("created_at"),
            }
        elif service_name == "notifications":
            # Prepare notification data
            return {
                "type": "email_received",
                "user_id": data.get("user_id"),
                "title": f"New email: {data.get('subject', 'No subject')}",
                "message": f"From: {data.get('from', 'Unknown sender')}",
                "timestamp": data.get("created_at"),
                "metadata": {
                    "email_id": data.get("id"),
                    "thread_id": data.get("thread_id"),
                    "folder": data.get("folder"),
                },
            }
        else:
            # Default: pass through original data
            return data

    def get_downstream_services(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all downstream services"""
        return {
            name: {
                "enabled": service.enabled,
                "endpoint": service.endpoint,
                "timeout": service.timeout,
            }
            for name, service in self.downstream_services.items()
        }
