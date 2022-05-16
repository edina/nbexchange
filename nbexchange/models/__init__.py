""" Module for handling all database models.

Notes:
    The models created with the inherited `Base` constant
    must be imported below the declaration for `Alembic`
    autogenerate to work.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .actions import Action  # noqa F401
from .assignments import Assignment  # noqa F401
from .courses import Course  # noqa F401
from .feedback import Feedback  # noqa F401
from .notebooks import Notebook  # noqa F401
from .subscriptions import Subscription  # noqa F401
from .users import User  # noqa F401
