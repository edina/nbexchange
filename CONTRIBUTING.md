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
* New features and backwards-incompatible changes should be very clearly documented.

Github does a pretty good job testing nbexchange and Pull Requests, but it may make sense to manually perform tests.

## Developing nbexchange

Whilst nbexchange can run under python>3.7, the developers of the system currently run under 3.11.

We suggest you set up an appropriate virtual environment.

To setup nbexchange for development, run:

```bash
pip install .[test]
```

or
```bash
pip install -e '.[test]'
```
if zsh or similar

When writing code, please don't rely on _code is its own documentation_ - particularly if you're doing anything remotely complicated.
A simple comment at the top is useful for future developers to know _why_ the code is doing something.

### Formatting code.

We use [`pre-commit`](https://pre-commit.com/) to ensure consistency.

All (appropriate) files are checked with `isort`, `black`, and `flake8`.

## Running Tests

Tests should be run locally before final commit & Pull Request is made.

GitHub `Actions` run Tests. These teste include checking that files are _linted_ to our preferred style: [black](https://github.com/psf/black)

When you add/change/improve functionality, please _please_ **please** write tests as well.

Tests should check that error cases are handled, and that [where applicable] both singular & multiple actions are handled correctly.

There is no such thing as _too many tests_

### Example testing process

This is how I test, using a virtual environment

```sh
pip install -r '.[test]'
pytest nbexchange
```

## Soak testing the exchange

Unit tests check methods and end-points, on an individual and singular level

To test that the exchange is happily handling large classes, we've included a script called `soak_trial.py`
(not `soak_test`, as the GitHub auto-testing routines assume any file with `test` in the name should be run... oops)

**This script is designed for EDINA's Noteable service - you will probably need to copy & edit for your own environment**

* The script assumes that the exchange is being run in a kubernetes cluster, and the tests are happening fromm a developers workstation.
    * This means the developer needs an accessible `kube-config` for that cluster
* By default, it wants to connect to the `default` namespace in EDINA's `dev` cluster - but these can be changed with command-line parameters.
* Noteable uses JWT tokens for authentication, so you'll need to edit the code to set up user authentication to match whatever you're using (ie, whatever you've got in `nbexchange/handlers/auth/????`)

### Usage

The script will auto-find the exchange server, and prompt for the magick to allow the script to connect.

The script is designed around reasonable higher-end numbers, based on what our customers are doing
* The Course & Assignment codes are randomely generated to avoid interacting with existing data
* The script defaults to 250 students
* The script has a single assignment file (4.3MB) plus an accompanying data-file (42KB)
* The script deletes records of it's run (as far as possible)
* Use `python soak_trial.py -h` for the list of parameters

Sample run (a single student):
```
❯ python soak_trial.py -s 1

Set up port forwarding
Please open a new terminal and run the following command(s):

    kubectl port-forward pod/naas-dev-nbexchange-5b67cc5759-m2mvv  9000:9000

.... and wait for the command to say it's forwarding - then press enter here to continue
WARNING:__main__:Looking good: Going to test 1 students in cluster 'noteable-dev', using nbexchange 'naas-dev-nbexchange-5b67cc5759-m2mvv'
WARNING:__main__:Instructor Release
WARNING:__main__:Students fetch and submit
WARNING:__main__:student_fetch called - username: 1-s000001
WARNING:__main__:student_submit called - username: 1-s000001
WARNING:__main__:instructor_collect called - username: 1-instructor
WARNING:__main__:collected 1-s000001
WARNING:__main__:instructor_release_feedback called - username: 1-instructor
WARNING:__main__:Uploaded feedback for 1-s000001 on assignment 1d9ac160-3400-470f-894d-90c245284b8a.
WARNING:__main__:student_fetch_feedback called - username: 1-s000001
WARNING:__main__:Finished: An assignment with 1 students has done 'release_assignment', 'fetch_assignment', 'submit', 'collect', 'release_feedback', and 'fetch_assignment'.
WARNING:__main__:Tidy_up called: assignment_id=1d9ac160-3400-470f-894d-90c245284b8a (keep_data?: False)
WARNING:__main__:We're purging the data.... so deleting files too
WARNING:__main__:
        SQL Tidy-up instructions, until the new 'purge' code is in the exchange

            delete from from assignment where assignment_code = '1d9ac160-3400-470f-894d-90c245284b8a';
        
```