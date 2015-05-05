# nppes_fhir_demo
A simple hack/demonstration of how to access provider directory (NPPES) via FHIR services

Requires:
- Elasticsearch - to serve as database for NPPES records (Lucene)
- Flask - simple python web server
- gunicorn - WSGI gateway to expose the Flask app to the web


Very brief instructions:
- Install Elasticsearch. I took all the defaults, which is overkill, but it works
- Pip install Flask, elasticsearch helper routines, and gunicorn
- Download the 5GB NPPES file from CMS, and edit "bulk_load_nppes" to point to it
- Run 'bulk_load_nppes', pointing to your local install of ElasticSearch. 3.7M records loads in about 5-6 minutes on my i7/SSD
- Run "serve_nppes' to test locally (defaults to 127.0.0.1:5000)
- Deploy to web by running gunicorn in front of serve_nppes


More details later...
  

## Dockerized version

### Requirements

 * Install docker (https://docs.docker.com/installation/)
 * Install docker-compose (https://docs.docker.com/compose/install/)

### Setup

 * Launch the stack: `docker-compose up`
 * Load sample data: `docker-compose run web /code/nppes_fhir_demo/load_data.py`
 * Try it: browse to http://host/nppes_fhir
 * View logs `docker-compose logs`
