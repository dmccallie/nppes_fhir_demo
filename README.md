# nppes_fhir_demo
A simple hack/demonstration of how to access provider directory (NPPES) via FHIR services

Requires:
- Elasticsearch - to serve as database for NPPES records (Lucene)
- Flask - simple python web server
- gunicorn - WSGI gateway to expose the Flask app to the web


Very brief instructions:
- Install and launch Elasticsearch. I took all the defaults, which is overkill, but it works
- Use python to "pip install" Flask, elasticsearch, and gunicorn
- run the "download.sh" script in NPPES_data to download the NPPES file from CMS, and the "taxonomy" file from NUCC. On the Mac, the unzip tool may not be able to handle the large CSV from NPPES, so you may need to manually extract with some other unzip tool. The unziped size is ~5GB
- Run 'bulk_load_nppes'
  - It should find the right CSV files.  If not, pass them in on the comand line.
  - It should default to point to your local install of ElasticSearch. If not, look in the code to see which environment variables to set to point to your instance of ES.
  - Loading the ~3.7M records takes about 5-6 minutes on my i7/SSD. Ignore the error messages about non-Ascii provider entries. That's a bug to be fixed, but obly drops a relatively few provider names. You only need to load the provider records into elasticsearch once, of course.
- Run "serve_nppes' to test locally (defaults to 127.0.0.1:5000/nppes_fhir)
- Deploy to web by running gunicorn to serve up serve_nppes:app (the WSGI entry point.)
  - `gunicorn -b 0.0.0.0:80 -w 4 serve_nppes:app` 


More details later...
  

## Dockerized version

### Requirements

 * Install docker (https://docs.docker.com/installation/)
 * Install docker-compose (https://docs.docker.com/compose/install/)

### Setup

 * Launch the stack: `docker-compose up`
 * Load sample data: `docker-compose run web /code/nppes_fhir_demo/load_data.py`
 * Try it: browse to http://container/nppes_fhir or http://host:8888/nppes_fhir
 * View logs `docker-compose logs`
