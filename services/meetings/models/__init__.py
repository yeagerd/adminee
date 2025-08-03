from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from services.common.database_config import is_sqlite_database
from services.meetings.models.base import Base as Base
from services.meetings.models.meeting import MeetingPoll as MeetingPoll
from services.meetings.models.meeting import PollParticipant as PollParticipant
from services.meetings.models.meeting import PollResponse as PollResponse
from services.meetings.models.meeting import TimeSlot as TimeSlot
from services.meetings.settings import get_settings


def get_engine() -> "Engine":
    db_url = get_settings().db_url_meetings

    # Apply strict SQLite configuration if using SQLite
    connect_args = {}
    if is_sqlite_database(db_url):
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
            "pragmas": {
                "foreign_keys": "ON",
                "journal_mode": "WAL",
                "synchronous": "NORMAL",
                "temp_store": "MEMORY",
            },
        }

    return create_engine(db_url, echo=False, future=True, connect_args=connect_args)


def get_sessionmaker() -> sessionmaker:
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Generator["Session", None, None]:
    Session = get_sessionmaker()
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
