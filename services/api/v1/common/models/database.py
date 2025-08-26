"""
Database models used across all services.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseWithTimestamps(Base):  # type: ignore[misc,valid-type]
    """Base class for models with timestamp fields."""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize model with keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
