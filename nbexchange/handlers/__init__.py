from nbexchange.handlers.assignment import Assignment, Assignments
from nbexchange.handlers.collection import Collection, Collections
from nbexchange.handlers.pages import EnvHandler, HomeHandler
from nbexchange.handlers.submission import Submission, Submissions
from nbexchange.handlers.user import User

default_handlers = [
    Assignment,
    Assignments,
    Collection,
    Collections,
    Submission,
    Submissions,
    # User,
    # EnvHandler,
    HomeHandler,
]
