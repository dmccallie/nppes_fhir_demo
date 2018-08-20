# nppes_fhir_demo
A simple hack/demonstration of how to search and access a locally-copied CMS provider directory (NPPES) via elasticsearch and early DST FHIR services

Addendum Aug 2018 - some additional hacks to this otherwise abandoned project:

- upgraded to python 3
- upgraded to elasticsearch 6.*
- added a few demo tweaks to the search form

NOTE what's still missing (and won't likely get added)

- does not support current FHIR resources - sorry, but this was merely to prove that it could be done!
- does not support the new CMS "endpoints" directory information
- does not support the relatively new CMS "additional names" and "secondary address" files


### Requires:

- Python 3
- Elasticsearch - to serve as database for NPPES records (Lucene)
- Flask - simple python web server
- gunicorn - WSGI gateway to expose the Flask app to the web


## Very brief instructions:

- Install and launch Elasticsearch. I took all the defaults, which is overkill, but it works. On the mac, 'brew' can install elasticsearch and kibana with no problems. To use the phonetic analyzer, you will also need to install the phonetic plugin, using something like this:
  - ```sudo bin/elasticsearch-plugin install analysis-phonetic```
- Use python to "pip install" Flask, elasticsearch, and gunicorn
- Run the "download.sh" script in NPPES_data to download the NPPES file from CMS, and the "taxonomy" file from NUCC. You might need to edit this file to refer to a more recent CMS distribution of the NPPES database!
- the bulk_load_nppes script can now read directly from the zip file, so there is no need to extract the 5GB CSV file
- Run 'python bulk_load_nppes'
  - It should find the right ZIP and CSV files.  If not, pass them in on the comand line.
  - It should default to point to your local install of ElasticSearch. If not, look in the code to see which environment variables to set to point to your instance of ES.
  - Loading the ~4.2M records takes about 5-6 minutes on my i7/SSD. Ignore the error messages about non-Ascii provider entries. That's a bug to be fixed, but obly drops a relatively few provider names. You only need to load the provider records into elasticsearch once, of course.
- Run "python serve_nppes' to test locally (defaults to 127.0.0.1:5000/nppes_fhir)
- Optionally deploy to web by running gunicorn to serve up serve_nppes:app (the WSGI entry point.)
  - `gunicorn -b 0.0.0.0:80 -w 4 serve_nppes:app` 


More details:

Set up git, Python 3, and elasticsearch (somewhere network accessible), then:

```
make sure elasticsearch is running somewhere accessible - the loader program will configure the necessary index
git clone https://github.com/dmccallie/nppes_fhir_demo/
cd nppes_fhir_demo
pip install -r requirements.txt
cd NPPES_data
sh ./download.sh
cd ../nppes_fhir_demo
python load_nppes_bulk.py

# in local env
python serve_nppes.py

# in prod
gunicorn -b 0.0.0.0:8080 serve_nppes:app
```

## Dockerized version - NOTE: this is NOT been kept up to date.  You will have to change some things.

### Requirements

 * Install docker (https://docs.docker.com/installation/)
 * Install docker-compose (https://docs.docker.com/compose/install/)

### Setup

 * Launch the stack: `docker-compose up`
 * Load sample data: `docker-compose run web /code/nppes_fhir_demo/load_data.sh`
 * Try it: browse to http://container/nppes_fhir or http://host:8888/nppes_fhir
 * View logs `docker-compose logs`
