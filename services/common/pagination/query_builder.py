"""
Cursor query builder for database operations.

This module provides database-agnostic query building patterns for
cursor-based pagination.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from .base import CursorInfo


class CursorQueryBuilder(ABC):
    """
    Abstract base class for building cursor-based database queries.

    This class provides common patterns for building cursor-based queries
    that work across different database backends.
    """

    @abstractmethod
    def build_cursor_filter(
        self, cursor_info: CursorInfo, id_column: str, timestamp_column: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build cursor-based filter conditions for database queries.

        Args:
            cursor_info: Cursor information containing position and direction
            id_column: Name of the ID column
            timestamp_column: Name of the timestamp column

        Returns:
            Tuple of (filter_condition, parameters)
        """
        pass

    @abstractmethod
    def build_ordering_clause(
        self, id_column: str, timestamp_column: str, direction: str = "next"
    ) -> str:
        """
        Build ordering clause for cursor-based pagination.

        Args:
            id_column: Name of the ID column
            timestamp_column: Name of the timestamp column
            direction: Pagination direction ('next' or 'prev')

        Returns:
            SQL ordering clause
        """
        pass

    @abstractmethod
    def build_limit_clause(self, limit: int) -> Tuple[str, Dict[str, Any]]:
        """
        Build limit clause for pagination.

        Args:
            limit: Number of items to return

        Returns:
            Tuple of (limit_clause, parameters)
        """
        pass

    def build_base_query(
        self,
        table_name: str,
        cursor_info: Optional[CursorInfo] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
        id_column: str = "id",
        timestamp_column: str = "updated_at",
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a complete cursor-based query.

        Args:
            table_name: Name of the table to query
            cursor_info: Optional cursor information for pagination
            additional_filters: Additional filter conditions
            id_column: Name of the ID column
            timestamp_column: Name of the timestamp column

        Returns:
            Tuple of (query_string, parameters)
        """
        # Start with base query
        query_parts = [f"SELECT * FROM {table_name}"]
        parameters = {}

        # Build WHERE clause
        where_conditions = []

        # Add cursor filter if provided
        if cursor_info:
            cursor_filter, cursor_params = self.build_cursor_filter(
                cursor_info, id_column, timestamp_column
            )
            where_conditions.append(cursor_filter)
            parameters.update(cursor_params)

        # Add additional filters
        if additional_filters:
            for key, value in additional_filters.items():
                if value is not None:
                    param_name = f"filter_{key}"
                    where_conditions.append(f"{key} = :{param_name}")
                    parameters[param_name] = value

        # Add WHERE clause if we have conditions
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))

        # Add ordering
        direction = cursor_info.direction if cursor_info else "next"
        ordering = self.build_ordering_clause(id_column, timestamp_column, direction)
        query_parts.append(f"ORDER BY {ordering}")

        # Add limit
        limit = cursor_info.limit if cursor_info else 20
        limit_clause, limit_params = self.build_limit_clause(limit)
        query_parts.append(limit_clause)
        parameters.update(limit_params)

        return " ".join(query_parts), parameters

    def build_count_query(
        self, table_name: str, additional_filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a count query for pagination metadata.

        Args:
            table_name: Name of the table to count
            additional_filters: Additional filter conditions

        Returns:
            Tuple of (query_string, parameters)
        """
        query_parts = [f"SELECT COUNT(*) FROM {table_name}"]
        parameters = {}

        # Add additional filters
        if additional_filters:
            where_conditions = []
            for key, value in additional_filters.items():
                if value is not None:
                    param_name = f"count_filter_{key}"
                    where_conditions.append(f"{key} = :{param_name}")
                    parameters[param_name] = value

            if where_conditions:
                query_parts.append("WHERE " + " AND ".join(where_conditions))

        return " ".join(query_parts), parameters


class SQLAlchemyCursorQueryBuilder(CursorQueryBuilder):
    """
    SQLAlchemy-specific implementation of cursor query builder.
    """

    def build_cursor_filter(
        self, cursor_info: CursorInfo, id_column: str, timestamp_column: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build cursor-based filter for SQLAlchemy queries.
        """
        if cursor_info.direction == "next":
            # For next page: (timestamp > last_timestamp) OR
            # (timestamp = last_timestamp AND id > last_id)
            filter_condition = (
                f"({timestamp_column} > :last_timestamp) OR "
                f"({timestamp_column} = :last_timestamp AND {id_column} > :last_id)"
            )
        else:
            # For previous page: (timestamp < last_timestamp) OR
            # (timestamp = last_timestamp AND id < last_id)
            filter_condition = (
                f"({timestamp_column} < :last_timestamp) OR "
                f"({timestamp_column} = :last_timestamp AND {id_column} < :last_id)"
            )

        parameters = {
            "last_timestamp": cursor_info.last_timestamp,
            "last_id": cursor_info.last_id,
        }

        return filter_condition, parameters

    def build_ordering_clause(
        self, id_column: str, timestamp_column: str, direction: str = "next"
    ) -> str:
        """
        Build ordering clause for SQLAlchemy queries.
        """
        if direction == "next":
            return f"{timestamp_column} ASC, {id_column} ASC"
        else:
            return f"{timestamp_column} DESC, {id_column} DESC"

    def build_limit_clause(self, limit: int) -> Tuple[str, Dict[str, Any]]:
        """
        Build limit clause for SQLAlchemy queries.
        """
        return "LIMIT :limit", {"limit": limit}


class PostgreSQLCursorQueryBuilder(SQLAlchemyCursorQueryBuilder):
    """
    PostgreSQL-specific implementation with additional optimizations.
    """

    def build_cursor_filter(
        self, cursor_info: CursorInfo, id_column: str, timestamp_column: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build cursor-based filter optimized for PostgreSQL.
        """
        # Use PostgreSQL's row comparison syntax for better performance
        if cursor_info.direction == "next":
            filter_condition = (
                f"({timestamp_column}, {id_column}) > (:last_timestamp, :last_id)"
            )
        else:
            filter_condition = (
                f"({timestamp_column}, {id_column}) < (:last_timestamp, :last_id)"
            )

        parameters = {
            "last_timestamp": cursor_info.last_timestamp,
            "last_id": cursor_info.last_id,
        }

        return filter_condition, parameters
