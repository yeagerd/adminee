"""Email processing state tracking models."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class EmailProcessingState(SQLModel, table=True):
    """Tracks email processing state for a user and provider."""

    __tablename__ = "email_processing_states"  # type: ignore[assignment]

    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4, primary_key=True, nullable=False
    )
    user_email: str = Field(max_length=255, nullable=False)
    provider: str = Field(max_length=50, nullable=False)  # 'gmail' or 'microsoft'
    last_processed_id: Optional[str] = Field(default=None, max_length=255)
    last_processed_timestamp: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    history_id: Optional[str] = Field(default=None, max_length=255)  # Gmail specific
    delta_link: Optional[str] = Field(default=None)  # Microsoft specific
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        ),
    )

    def __repr__(self):
        return f"<EmailProcessingState(user_email='{self.user_email}', provider='{self.provider}')>"
