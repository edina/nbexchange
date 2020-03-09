# Contributing to nbexchange

We're thrilled you want to contribute to this nbgrader exchange package.

## Opening an Issue

When opening a new Issue, please take the following steps:

1. Search GitHub and/or Google for your issue to avoid duplicate reports. Keyword searches for your error messages are most helpful.

1. If possible, try updating to master and reproducing your issue, because we may have already fixed it.

1. Try to include a minimal reproducible test case.

## Pull Requests

Some guidelines on contributing to nbexchange:

* All work is submitted via Pull Requests.
* Pull Requests should be submitted as soon as there is code worth discussing. Pull Requests track the branch, so you can continue to work after the PR is submitted. Review and discussion can begin well before the work is complete, and the more discussion the better. The worst case is that the PR is closed.
* Pull Requests should generally be made against master
* Pull Requests should be tested, if feasible:
    * bugfixes should include regression tests.
    * new behavior should at least get minimal exercise.
* New features and backwards-incompatible changes should be documented by adding a new file to the pr directory, see the README.md there for details.
* Code 

Travis does a pretty good job testing nbexchange and Pull Requests, but it may make sense to manually perform tests.

## Running Tests

Tests should be run locally before final commit & Pull Request is made.

Tests include checking that files are _linted_ to our preferred style: [black](https://github.com/psf/black)

Tests should check that error cases are handled, and that [where applicable] both singular & multiple actions are handled correctly.

There is no such thing as _too many tests_

### Example testing process

This is how I test, using a virtual environment

```sh
source venv/bin/activate
pip install -r requirements.txt
pytest nbexchange
```