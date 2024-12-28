FROM python:3.10-slim-buster

WORKDIR /ontomo

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# COPY app ./app
# COPY run.py .

ENV GRAPHDB_HOST graphdb
ENV FLASK_DEBUG True
ENV FLASK_APP run.py

CMD ["python3", "-m" , "flask", "run", "--host=0.0.0.0"]