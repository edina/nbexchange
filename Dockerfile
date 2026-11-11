# FROM python:3.13.15-slim-trixie
# 3.15.2-slim-trixie / amd64 @ 2026-11-11
FROM python@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

RUN apt update && \
    apt install -yq make build-essential \
    libbz2-dev libffi-dev liblzma-dev libreadline-dev \
    libncursesw5-dev libsqlite3-dev libssl-dev libxml2-dev libxmlsec1-dev  \
    curl git tk-dev xz-utils zlib1g-dev \
    && apt-get upgrade perl-base \
    && rm -rf /var/lib/apt/lists/*


ARG COMMIT=""
LABEL commit=${COMMIT}
RUN pip install --upgrade pip

WORKDIR /usr/src/app

# Sqlite for testing
RUN apt update && apt install  --yes --quiet --no-install-recommends sqlite3 && rm -rf /var/lib/apt/lists/*

# Supervisord
RUN pip install supervisor
COPY supervisord.conf /usr/src/app

# Copy package
COPY pyproject.toml README.md LICENSE /usr/src/app/
COPY nbexchange /usr/src/app/nbexchange
# Install dependencies
RUN pip install .

# Set commit sha as an environment variable
ENV COMMIT_SHA=${COMMIT}

EXPOSE 9000

CMD ["supervisord", "-n", "-c", "/usr/src/app/supervisord.conf"]