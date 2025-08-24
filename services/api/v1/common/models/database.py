"""
Database models used across all services.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseWithTimestamps:
    """Base class for models with timestamp fields."""

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize model with keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
