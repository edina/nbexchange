FROM python:3.11.7-slim-bullseye

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

