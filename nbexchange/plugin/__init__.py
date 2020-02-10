"""
nbgrader authenticator that uses EDINAs noteable service.

After installation, you can enable it by adding:

    c.Authenticator.plugin_class = NoteableAuthPlugin

in your root `nbgrader_config.py` file.
"""
from .exchange import ExchangeError, Exchange
from .submit import ExchangeSubmit
from .release_feedback import ExchangeReleaseFeedback
from .release import ExchangeRelease
from .release_assignment import ExchangeReleaseAssignment
from .fetch_feedback import ExchangeFetchFeedback
from .fetch import ExchangeFetch
from .fetch_assignment import ExchangeFetchAssignment
from .collect import ExchangeCollect
from .list import ExchangeList

__all__ = [
    "Exchange",
    "ExchangeError",
    "ExchangeCollect",
    "ExchangeFetch",
    "ExchangeFetchAssignment",
    "ExchangeFetchFeedback",
    "ExchangeList",
    "ExchangeRelease",
    "ExchangeReleaseAssignment",
    "ExchangeReleaseFeedback",
    "ExchangeSubmit"
]