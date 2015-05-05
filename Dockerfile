FROM python:2.7
RUN wget http://nppes.viva-it.com/NPPES_Data_Dissemination_April_2015.zip
RUN apt-get update && apt-get install unzip
RUN unzip NPPES_Data_Dissemination_April_2015.zip && \
    rm NPPES_Data_Dissemination_April_2015.zip && \
    mkdir /data && \
    mv npidata_20050523-20150412.csv /data

ADD . /code
WORKDIR /code/
RUN pip install -r requirements.txt

WORKDIR /code/nppes_fhir_demo
