"""This module exports the database engine.

Notes:
     Using the scoped_session contextmanager is
     best practice to ensure the session gets closed
     and reduces noise in code by not having to manually
     commit or rollback the db if a exception occurs.
"""

import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from nbexchange.models import Base

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_engine(db_url: Optional[str] = None, **kwargs) -> Engine:
    """Get or create the database engine.

    Uses lazy initialization to avoid side effects at import time.

    Args:
        db_url: Database URL. Defaults to NBEX_DB_URL env var or sqlite memory.
        **kwargs: Additional arguments passed to create_engine.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine

    if _engine is None:
        db_url = db_url or os.environ.get("NBEX_DB_URL", "sqlite:///:memory:")
        _engine = create_engine(db_url, **kwargs)

    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory.

    Uses lazy initialization to avoid side effects at import time.

    Returns:
        SQLAlchemy sessionmaker instance.
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)

    return _session_factory


def init_db(db_url: Optional[str] = None, reset: bool = False, **kwargs) -> Engine:
    """Initialize the database engine and create tables.

    Args:
        db_url: Database URL. Defaults to NBEX_DB_URL env var or sqlite memory.
        reset: If True, drop all tables before creating.
        **kwargs: Additional arguments passed to create_engine.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine, _session_factory

    _engine = create_engine(db_url or os.environ.get("NBEX_DB_URL", "sqlite:///:memory:"), **kwargs)

    if reset:
        Base.metadata.drop_all(_engine)

    Base.metadata.create_all(_engine)
    _session_factory = sessionmaker(bind=_engine)

    return _engine


@contextmanager
def scoped_session() -> Session:
    """Context manager for database sessions.

    Automatically commits on success, rolls back on exception, and closes session.

    Yields:
        SQLAlchemy Session instance.

    Example:
        with scoped_session() as session:
            user = User(name="test")
            session.add(user)
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
