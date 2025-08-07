"""
Shipments-specific cursor pagination implementation.

This module provides shipments-specific cursor pagination functionality
extending the common base pagination.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from services.common.pagination.base import BaseCursorPagination, CursorInfo
from services.common.pagination.query_builder import PostgreSQLCursorQueryBuilder
from services.common.pagination.schemas import PaginationConfig


def _parse_iso_datetime(dt_str: str) -> datetime:
    """
    Parse ISO datetime string to datetime object.

    Args:
        dt_str: ISO datetime string

    Returns:
        datetime object with timezone info

    Raises:
        ValueError: If the string cannot be parsed
    """
    try:
        # Try parsing with timezone info
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        # Try parsing without timezone info (assume UTC)
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc)


class ShipmentsCursorPagination(BaseCursorPagination):
    """Shipments-specific cursor pagination implementation."""

    def __init__(self, config: PaginationConfig):
        """Initialize shipments pagination with configuration."""
        super().__init__(config)
        self.query_builder = PostgreSQLCursorQueryBuilder()

    def build_query_filters(self, cursor_info: CursorInfo) -> Dict[str, Any]:
        """
        Build database query filters based on cursor information.

        Args:
            cursor_info: Cursor information containing filters and position

        Returns:
            Dictionary of query filters
        """
        filters: Dict[str, Any] = {}

        # Add cursor-based position filters
        if cursor_info.direction == "next":
            # For next page: (updated_at > last_updated) OR
            # (updated_at = last_updated AND id > last_id)
            filters["cursor_filter"] = (
                "(updated_at > :last_updated) OR "
                "(updated_at = :last_updated AND id > :last_id)"
            )
            filters["cursor_params"] = {
                "last_updated": _parse_iso_datetime(cursor_info.last_timestamp),
                "last_id": cursor_info.last_id,
            }
        else:
            # For previous page: (updated_at < last_updated) OR
            # (updated_at = last_updated AND id < last_id)
            filters["cursor_filter"] = (
                "(updated_at < :last_updated) OR "
                "(updated_at = :last_updated AND id < :last_id)"
            )
            filters["cursor_params"] = {
                "last_updated": _parse_iso_datetime(cursor_info.last_timestamp),
                "last_id": cursor_info.last_id,
            }

        # Add shipments-specific filters from cursor
        shipments_filters = cursor_info.filters

        # Carrier filter
        if "carrier" in shipments_filters and shipments_filters["carrier"]:
            filters["carrier"] = shipments_filters["carrier"]

        # Status filter
        if "status" in shipments_filters and shipments_filters["status"]:
            filters["status"] = shipments_filters["status"]

        # Tracking number filter
        if (
            "tracking_number" in shipments_filters
            and shipments_filters["tracking_number"]
        ):
            filters["tracking_number"] = shipments_filters["tracking_number"]

        # User ID filter
        if "user_id" in shipments_filters and shipments_filters["user_id"]:
            filters["user_id"] = shipments_filters["user_id"]

        # Email message ID filter
        if (
            "email_message_id" in shipments_filters
            and shipments_filters["email_message_id"]
        ):
            filters["email_message_id"] = shipments_filters["email_message_id"]

        return filters

    def get_ordering_clause(self, direction: str = "next") -> str:
        """
        Get the database ordering clause for shipments pagination.

        Args:
            direction: Pagination direction ('next' or 'prev')

        Returns:
            SQL ordering clause
        """
        if direction == "next":
            return "updated_at ASC, id ASC"
        else:
            return "updated_at DESC, id DESC"

    def create_shipments_cursor_info(
        self,
        last_id: str,
        updated_at: Union[str, datetime],
        filters: Dict[str, Any],
        direction: str = "next",
        limit: int = None,
    ) -> CursorInfo:
        """
        Create cursor information specific to shipments.

        Args:
            last_id: UUID of last package in current page
            updated_at: ISO timestamp for consistent ordering
            filters: JSON string of active filters (carrier, status, etc.)
            direction: 'next' or 'prev'
            limit: Number of items per page

        Returns:
            CursorInfo object
        """
        return self.create_cursor_info(
            last_id=last_id,
            last_timestamp=updated_at,
            filters=filters,
            direction=direction,
            limit=limit,
        )

    def build_shipments_query(
        self,
        cursor_info: Optional[CursorInfo] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build a complete shipments query with cursor pagination.

        Args:
            cursor_info: Optional cursor information for pagination
            additional_filters: Additional filter conditions

        Returns:
            Tuple of (query_string, parameters)
        """
        return self.query_builder.build_base_query(
            table_name="packages",
            cursor_info=cursor_info,
            additional_filters=additional_filters,
            id_column="id",
            timestamp_column="updated_at",
        )

    def create_shipments_pagination_response(
        self,
        packages: List[Any],
        cursor_info: Optional[CursorInfo] = None,
        has_next: bool = False,
        has_prev: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a shipments-specific pagination response.

        Args:
            packages: List of package objects
            cursor_info: Current cursor information
            has_next: Whether there are more packages after this page
            has_prev: Whether there are packages before this page

        Returns:
            Dictionary with packages and pagination metadata
        """
        response = self.create_pagination_response(
            items=packages,
            cursor_info=cursor_info,
            has_next=has_next,
            has_prev=has_prev,
        )

        # Rename 'items' to 'packages' for shipments API
        response["packages"] = response.pop("items")

        return response

    def validate_shipments_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize shipments-specific filters.

        Args:
            filters: Raw filter dictionary

        Returns:
            Sanitized filter dictionary
        """
        validated_filters = {}

        # Validate carrier filter
        if "carrier" in filters and filters["carrier"]:
            carrier = str(filters["carrier"]).strip()
            if carrier:
                validated_filters["carrier"] = carrier

        # Validate status filter
        if "status" in filters and filters["status"]:
            status = str(filters["status"]).strip()
            if status:
                validated_filters["status"] = status

        # Validate tracking number filter
        if "tracking_number" in filters and filters["tracking_number"]:
            tracking_number = str(filters["tracking_number"]).strip()
            if tracking_number:
                # Normalize tracking number for consistent matching
                from services.shipments.utils import normalize_tracking_number

                # Get carrier for proper normalization
                carrier_for_normalization: Optional[str] = None
                carrier_raw = filters.get("carrier")
                if carrier_raw is not None:
                    carrier_for_normalization = str(carrier_raw)
                validated_filters["tracking_number"] = normalize_tracking_number(
                    tracking_number, carrier_for_normalization
                )

        # Validate user ID filter
        if "user_id" in filters and filters["user_id"]:
            user_id = str(filters["user_id"]).strip()
            if user_id:
                validated_filters["user_id"] = user_id

        # Validate email message ID filter
        if "email_message_id" in filters and filters["email_message_id"]:
            email_message_id = str(filters["email_message_id"]).strip()
            if email_message_id:
                validated_filters["email_message_id"] = email_message_id

        return validated_filters
