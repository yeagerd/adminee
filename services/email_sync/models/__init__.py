"""Email sync models."""

from sqlmodel import SQLModel
from services.email_sync.models.email_tracking import EmailProcessingState

__all__ = ["SQLModel", "EmailProcessingState"] 