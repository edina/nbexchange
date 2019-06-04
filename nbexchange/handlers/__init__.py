from nbexchange.handlers.assignment import Assignment, Assignments
from nbexchange.handlers.collection import Collection, Collections
from nbexchange.handlers.pages import HomeHandler
from nbexchange.handlers.submission import Submission, Submissions

default_handlers = [
    Assignment,
    Assignments,
    Collection,
    Collections,
    Submission,
    Submissions,
    HomeHandler,
]
