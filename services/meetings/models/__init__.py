from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from services.meetings.models.base import Base as Base
from services.meetings.models.meeting import MeetingPoll as MeetingPoll
from services.meetings.models.meeting import PollParticipant as PollParticipant
from services.meetings.models.meeting import PollResponse as PollResponse
from services.meetings.models.meeting import TimeSlot as TimeSlot
from services.meetings.settings import get_settings


def get_engine() -> "Engine":
    db_url = get_settings().db_url_meetings
    return create_engine(db_url, echo=False, future=True)


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
