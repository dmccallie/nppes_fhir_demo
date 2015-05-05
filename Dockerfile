FROM python:2.7
RUN apt-get update && apt-get install unzip
ADD ./requirements.txt ./nppes_fhir_demo /code/
WORKDIR /code/
RUN pip install -r requirements.txt
VOLUME /data
WORKDIR /code/nppes_fhir_demo
