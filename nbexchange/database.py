"""This module exports the database engine.

Notes:
     Using the scoped_session contextmanager is
     best practice to ensure the session gets closed
     and reduces noise in code by not having to manually
     commit or rollback the db if a exception occurs.
"""

import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from nbexchange.models import Base

engine = create_engine(os.environ.get("NBEX_DB_URL", "sqlite:///:memory:"))
Base.metadata.create_all(engine)

# Session to be used throughout app.
Session = sessionmaker(bind=engine)


@contextmanager
def scoped_session():
    session = Session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as err:
        logging.error("Database session rollback due to: ", str(err))
        raise
    except Exception as err:
        session.rollback()
        logging.error("Unexpected error: ", str(err))
        raise
    finally:
        session.close()
