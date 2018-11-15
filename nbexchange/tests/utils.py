# async-request utility from jupyterhub.tests.utils v0.8.1
# used under BSD license

from concurrent.futures import ThreadPoolExecutor
import requests


class _AsyncRequests:
    """Wrapper around requests to return a Future from request methods
    A single thread is allocated to avoid blocking the IOLoop thread.
    """

    _session = None

    def __init__(self):
        self.executor = ThreadPoolExecutor(1)

    def set_session(self):
        self._session = requests.Session()

    def delete_session(self):
        self._session = None

    def __getattr__(self, name):
        if self._session is not None:
            requests_method = getattr(self._session, name)
        else:
            requests_method = getattr(requests, name)
        return lambda *args, **kwargs: self.executor.submit(
            requests_method, *args, **kwargs
        )

    def iter_lines(self, response):
        """Asynchronously iterate through the lines of a response"""
        it = response.iter_lines()
        while True:
            yield self.executor.submit(lambda: next(it))


# async_requests.get = requests.get returning a Future, etc.
async_requests = _AsyncRequests()
