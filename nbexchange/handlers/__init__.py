from nbexchange.handlers.assignment import Assignment, Assignments
from nbexchange.handlers.collection import Collection, Collections
from nbexchange.handlers.feedback import FeedbackHandler
from nbexchange.handlers.history import History
from nbexchange.handlers.pages import HomeHandler
from nbexchange.handlers.submission import Submission, Submissions

default_handlers = [
    Assignment,
    Assignments,
    Collection,
    Collections,
    History,
    Submission,
    Submissions,
    HomeHandler,
    FeedbackHandler,
]
