"""
PostgreSQL URL construction utilities.

This module provides a unified interface for constructing database connection URLs
for all services in the application. It uses services.common.config_secrets for
credential retrieval and supports both service and migration connections.
"""

import logging

from services.common.config_secrets import get_secret

logger = logging.getLogger(__name__)


class PostgresURLs:
    """Centralized PostgreSQL URL construction for all services."""

    def __init__(self) -> None:
        """Initialize the PostgresURLs instance."""
        pass

    def get_service_url(self, service_name: str) -> str:
        """
        Get the database URL for a specific service (limited permissions).

        Args:
            service_name: The service name (e.g., 'user', 'meetings', 'chat')

        Returns:
            PostgreSQL connection string for the service

        Raises:
            ValueError: If service_name is empty or invalid
        """
        if not service_name or not service_name.strip():
            raise ValueError("service_name cannot be empty")

        service_name = service_name.lower().strip()

        # Get credentials from config_secrets
        password = get_secret(f"BRIEFLY_{service_name.upper()}_SERVICE_PASSWORD")
        host = get_secret("POSTGRES_HOST", "localhost")
        port = get_secret("POSTGRES_PORT", "5432")

        if not password:
            logger.warning(f"No password found for service {service_name}")
            password = "no_password_set"

        return f"postgresql://briefly_{service_name}_service:{password}@{host}:{port}/briefly_{service_name}"

    def get_migration_url(self, service_name: str) -> str:
        """
        Get the database URL for migrations (admin permissions).

        Args:
            service_name: The service name (e.g., 'user', 'meetings', 'chat')

        Returns:
            PostgreSQL connection string for migrations with admin privileges

        Raises:
            ValueError: If service_name is empty or invalid
        """
        if not service_name or not service_name.strip():
            raise ValueError("service_name cannot be empty")

        service_name = service_name.lower().strip()

        # Get admin credentials from config_secrets
        admin_user = get_secret("POSTGRES_USER", "postgres")
        admin_password = get_secret("POSTGRES_PASSWORD", "postgres")
        host = get_secret("POSTGRES_HOST", "localhost")
        port = get_secret("POSTGRES_PORT", "5432")

        if not admin_password:
            logger.warning("No admin password found, using default")
            admin_password = "postgres"

        return f"postgresql://{admin_user}:{admin_password}@{host}:{port}/briefly_{service_name}"

    def get_readonly_url(self, service_name: str) -> str:
        """
        Get the database URL for read-only operations (if needed).

        Args:
            service_name: The service name (e.g., 'user', 'meetings', 'chat')

        Returns:
            PostgreSQL connection string for read-only operations

        Raises:
            ValueError: If service_name is empty or invalid
        """
        if not service_name or not service_name.strip():
            raise ValueError("service_name cannot be empty")

        service_name = service_name.lower().strip()

        # Get read-only credentials from config_secrets
        readonly_password = get_secret("BRIEFLY_READONLY_PASSWORD")
        host = get_secret("POSTGRES_HOST", "localhost")
        port = get_secret("POSTGRES_PORT", "5432")

        if not readonly_password:
            logger.warning("No read-only password found, falling back to service user")
            return self.get_service_url(service_name)

        return f"postgresql://briefly_readonly:{readonly_password}@{host}:{port}/briefly_{service_name}"

    def get_all_service_urls(self) -> dict[str, str]:
        """
        Get database URLs for all services.

        Returns:
            Dictionary mapping service names to their database URLs
        """
        services = [
            "user",
            "meetings",
            "shipments",
            "office",
            "chat",
            "contacts",
            "vector",
        ]
        return {service: self.get_service_url(service) for service in services}

    def get_all_migration_urls(self) -> dict[str, str]:
        """
        Get migration URLs for all services.

        Returns:
            Dictionary mapping service names to their migration URLs
        """
        services = [
            "user",
            "meetings",
            "shipments",
            "office",
            "chat",
            "contacts",
            "vector",
        ]
        return {service: self.get_migration_url(service) for service in services}
