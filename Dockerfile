FROM python:2.7
RUN apt-get update && apt-get install unzip
ADD . /code/
WORKDIR /code/
RUN pip install -r requirements.txt
RUN pip install gunicorn
VOLUME /data
WORKDIR /code/nppes_fhir_demo
EXPOSE 80
CMD ["gunicorn","-b","0.0.0.0:80", "serve_nppes:app"]
