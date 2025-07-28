"""Database configuration for email sync service."""

import os

from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

from services.email_sync.models.email_tracking import EmailProcessingState  # noqa: F401


def get_engine():
    """Get the database engine."""
    database_url = os.getenv(
        "EMAIL_TRACKING_DATABASE_URL", "sqlite:///email_tracking.db"
    )
    return create_engine(database_url, echo=False, future=True)


def get_session() -> Session:
    """Get a database session."""
    engine = get_engine()
    return Session(engine)


def init_db():
    """Initialize the database by creating all tables."""
    engine = get_engine()
    SQLModel.metadata.create_all(bind=engine)
