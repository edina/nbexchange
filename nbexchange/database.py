""" This module exports the database engine.

Notes:
     Using the scoped_session contextmanager is
     best practice to ensure the session gets closed
     and reduces noise in code by not having to manually
     commit or rollback the db if a exception occurs.
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nbexchange.models import Base

engine = create_engine(os.environ.get("NBEX_DB_URL", "sqlite:///:memory:"))
# print(f"database.py Engine created! NBEX_DB_URL: {os.environ.get('NBEX_DB_URL')}")
Base.metadata.create_all(engine)
# print("database.py create_all(engine) ran")

# Session to be used throughout app.
Session = sessionmaker(bind=engine)
# print("database.py Session object created")


@contextmanager
def scoped_session():
    # print("database.scoped_session called")
    session = Session()
    # print(f"database.scoped_session have session {session}")
    try:
        # print("database.scoped_session ready to yield session")
        yield session
        # print("database.scoped_session about to commit session")
        session.commit()
        # print("database.scoped_session session commited")
    except Exception:
        # print("database.scoped_session about to rollback session")
        session.rollback()
        raise
    finally:
        # print("database.scoped_session about to close session")
        session.close()
