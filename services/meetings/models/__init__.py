from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .meeting import *

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

def get_engine():
    db_url = os.environ.get("MEETINGS_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meetings_db")
    return create_engine(db_url, echo=False, future=True)

def get_sessionmaker():
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

@contextmanager
def get_session():
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
