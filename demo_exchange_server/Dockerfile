FROM python:3.7

RUN apt update && apt install git sqlite3 -y

ADD . /src/nbexchange
RUN cd /src/nbexchange && python setup.py install

COPY demo_exchange_server/nbexchange_config.py .

CMD nbexchange
