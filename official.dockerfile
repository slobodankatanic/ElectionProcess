FROM python:3

RUN mkdir -p /opt/src/official

WORKDIR /opt/src/official

COPY applications/official.py ./official.py
COPY applications/configuration.py ./configuration.py
COPY applications/models.py ./models.py
COPY applications/requirements.txt ./requirements.txt
COPY applications/rightAccess.py ./rightAccess.py

RUN pip install -r ./requirements.txt

ENTRYPOINT ["python", "./official.py"]