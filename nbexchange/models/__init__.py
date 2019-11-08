""" Module for handling all database models.

Notes:
    The models created with the inherited `Base` constant
    must be imported below the declaration for `Alembic`
    autogenerate to work.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from nbexchange.models.actions import Action
from nbexchange.models.assignments import Assignment
from nbexchange.models.courses import Course
from nbexchange.models.notebooks import Notebook
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User
from nbexchange.models.feedback import Feedback
