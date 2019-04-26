FROM python:3.7

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
RUN pip install -r requirements.txt

EXPOSE 9000

CMD ["supervisord", "-n", "-c", "/usr/src/app/supervisord.conf"]

