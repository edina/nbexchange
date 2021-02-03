#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

import io
import os
import sys
from shutil import rmtree

from setuptools import find_packages, setup, Command

# Package meta-data.
NAME = "nbexchange"
DESCRIPTION = "Jupyterhub extension that provides an exchange service for nbgrader."
URL = "https://github.com/edina/nbexchange"
EMAIL = "Ian.Stuart@ed.ac.uk"
AUTHOR = "Edina Development team"
REQUIRES_PYTHON = ">=3.7.0"
VERSION = None

# What packages are required for this module to be executed?
REQUIRED = [
    "alembic",
    "aiocontextvars",
    "tornado",
    "psycopg2-binary",
    "ipykernel==5.4.3",
    "jupyterhub",
    "sentry-sdk==0.19.1",
    "sqlalchemy==1.3.20",
    "nbgrader==0.7.0.dev0",
    "urllib3==1.25.11", # Pinned because of requests depdendency conflict
    "pyjwt",
]

# What packages are required for testing?
TESTING = [
    "pytest",
    "pytest-cov",
    "pytest-tornado",
    "pytest-docker-tools",
    "beautifulsoup4",
    "html5lib",
    "psycopg2-binary",
    "mock",
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}


def get_package_data():
    """Get package data
    (mostly alembic config)
    """
    package_data = {}
    package_data["nbexchange"] = ["alembic.ini", "alembic/*", "alembic/versions/*"]
    return package_data


# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!


here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, NAME, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(about["__version__"]))
        os.system("git push --tags")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=("tests",)),
    package_data=get_package_data(),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],
    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
    setup_requires=["pytest-runner"],
    install_requires=REQUIRED,
    tests_require=TESTING,
    extras_require=EXTRAS,
    include_package_data=True,
    license="MIT",
    scripts=["scripts/nbexchange"],
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    dependency_links=[
        "https://github.com/jupyter/nbgrader/tarball/master#egg=nbgrader-0.7.0.dev0"
    ],
    # $ setup.py publish support.
    cmdclass={"upload": UploadCommand},
)
