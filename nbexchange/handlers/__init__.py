from nbexchange.handlers.assignment import Assignment, Assignments
from nbexchange.handlers.collection import Collection, Collections
from nbexchange.handlers.feedback import FeedbackHandler
from nbexchange.handlers.pages import HomeHandler
from nbexchange.handlers.submission import Submission, Submissions
from nbexchange.handlers.history import History

default_handlers = [
    Assignment,
    Assignments,
    Collection,
    Collections,
    Submission,
    Submissions,
    HomeHandler,
    FeedbackHandler,
    History,
]
