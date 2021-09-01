FROM python:3

RUN mkdir -p /opt/src/deamon

WORKDIR /opt/src/deamon

COPY applications/deamon.py ./deamon.py
COPY applications/configuration.py ./configuration.py
COPY applications/models.py ./models.py
COPY applications/requirements.txt ./requirements.txt
# COPY applications/rightAccess.py ./rightAccess.py

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "./deamon.py"]