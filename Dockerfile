FROM python:3.9

ARG COMMIT=""
LABEL commit=${COMMIT}

WORKDIR /usr/src/app

# Supervisord
RUN pip install supervisor
COPY supervisord.conf /usr/src/app

# Copy package
COPY setup.py /usr/src/app
COPY requirements.txt /usr/src/app
COPY scripts /usr/src/app/scripts
COPY nbexchange /usr/src/app/nbexchange
# Install dependencies
RUN python setup.py install

# Set commit sha as an environment variable
ENV COMMIT_SHA=${COMMIT}

EXPOSE 9000

CMD ["supervisord", "-n", "-c", "/usr/src/app/supervisord.conf"]

