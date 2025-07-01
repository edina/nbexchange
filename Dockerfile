#FROM python:3.11.7-slim-bullseye

# Know vuln in "pam"
FROM python:3.13.5-slim-bullseye

RUN apt update && \
    apt install -yq make build-essential \
    libbz2-dev libffi-dev liblzma-dev libreadline-dev \
    libncursesw5-dev libsqlite3-dev libssl-dev libxml2-dev libxmlsec1-dev  \
    curl git tk-dev xz-utils zlib1g-dev

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

