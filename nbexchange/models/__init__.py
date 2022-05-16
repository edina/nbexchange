""" Module for handling all database models.

Notes:
    The models created with the inherited `Base` constant
    must be imported below the declaration for `Alembic`
    autogenerate to work.
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# E402 : module level import not at top of file
# F401 : module imported but unused
from .actions import Action  # noqa: E402 F401
from .assignments import Assignment  # noqa: E402 F401
from .courses import Course  # noqa: E402 F401
from .feedback import Feedback  # noqa: E402 F401
from .notebooks import Notebook  # noqa: E402 F401
from .subscriptions import Subscription  # noqa: E402 F401
from .users import User  # noqa: E402 F401
