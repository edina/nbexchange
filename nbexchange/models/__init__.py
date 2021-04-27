""" Module for handling all database models.

Notes:
    The models created with the inherited `Base` constant
    must be imported below the declaration for `Alembic`
    autogenerate to work.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from .actions import Action
from .assignments import Assignment
from .courses import Course
from .feedback import Feedback
from .notebooks import Notebook
from .subscriptions import Subscription
from .users import User
