"""
nbgrader authenticator that uses EDINAs noteable service.

After installation, you can enable it by adding:

    c.Authenticator.plugin_class = NoteableAuthPlugin

in your root `nbgrader_config.py` file.
"""
from .collect import ExchangeCollect
from .exchange import Exchange, ExchangeError
from .fetch import ExchangeFetch
from .fetch_assignment import ExchangeFetchAssignment
from .fetch_feedback import ExchangeFetchFeedback
from .list import ExchangeList
from .release import ExchangeRelease
from .release_assignment import ExchangeReleaseAssignment
from .release_feedback import ExchangeReleaseFeedback
from .submit import ExchangeSubmit

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
    "ExchangeSubmit",
]
