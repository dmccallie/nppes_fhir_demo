import csv
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import time

nppes_file = "/data/npidata_20050523-20150412.csv" #download this 5GB file from CMS!
nucc_file  = "../NPPES_data/nucc_taxonomy_150.csv"

#this is the reference data used to specificy provider's specialties
def load_taxonomy(nucc):
	nucc_dict = {}
	with open(nucc) as nucc_file:
		nucc_reader = csv.DictReader(nucc_file)
		for row in nucc_reader:
			code = row['Code']
			classification = row['Classification']
			specialization = row['Specialization']
			if code and classification:
				nucc_dict[code] = classification + " " + specialization
	return nucc_dict

def get_specialty(nucc_dict, code_1, code_2, code_3):
	#just concatenate together for now
	#print (code_1, code_2, code_3)
	out = ""
	if (code_1):
		out += nucc_dict[code_1]
		if (code_2):
			out += " / " + nucc_dict[code_2]
			if (code_3):
				out += " / " + nucc_dict[code_3]
	return out

def extract_provider(row, nucc_dict):
	#creates the Lucene "document" to define this provider
	#assumes this is a valid provider
	provider_document = {}
	provider_document['npi'] = row['NPI']
	provider_document['firstname'] = row['Provider First Name']
	provider_document['lastname'] = row['Provider Last Name (Legal Name)']
	provider_document['mail_address_1'] = row['Provider First Line Business Mailing Address']
	provider_document['mail_address_2'] = row['Provider Second Line Business Mailing Address']
	provider_document['city'] = row['Provider Business Mailing Address City Name']
	provider_document['state_abbrev'] = row['Provider Business Mailing Address State Name']
	provider_document['credential'] = row['Provider Credential Text'].translate(None,".")
	provider_document['spec_1'] = nucc_dict.get(row['Healthcare Provider Taxonomy Code_1'],'') 
	provider_document['spec_2'] = nucc_dict.get(row['Healthcare Provider Taxonomy Code_2'],'')
	provider_document['spec_3'] = nucc_dict.get(row['Healthcare Provider Taxonomy Code_3'],'')

	#pseudo field for searching any part of an address
	#by creating this as one field, it's easy to do wildcard searches on any combination of inputs
	#but it does waste a few hundred MB.
	provider_document['full_address'] = provider_document['mail_address_1'] + " " + \
										provider_document['mail_address_2'] + " " + \
										provider_document['city'] + " " + \
										provider_document['state_abbrev']

	return provider_document

def convert_to_json(row, nucc_dict):
	#some kind of funky problem with non-ascii strings here
	#trap and reject any records that aren't full ASCII.
	#fix me!
	try:
		provider_doc = extract_provider(row, nucc_dict)
		j = json.dumps(provider_doc, ensure_ascii=True)
	except Exception, e:
		print "FAILED convert a provider record to ASCII = ", row['NPI']
		j = None
	return j

#create a python iterator for ES's bulk load function
def iter_nppes_data(nppes_file, nucc_dict, convert_to_json):
	with open(nppes_file) as csvfile:
		reader = csv.DictReader(csvfile)
		for row in reader:
			if not row['NPI Deactivation Date'] and row['Entity Type Code'] == '1':
				if (row['Provider Last Name (Legal Name)']):
					npi = row['NPI']
					body = convert_to_json(row, nucc_dict)
					if (body):
						#action instructs the bulk loader how to handle this record
						action =  {
        					"_index": "nppes",
        					"_type": "provider",
        					"_id": npi,
        					"_source": body
        				}
            			yield action
 	

#main code starts here

count = 0
nucc_dict = load_taxonomy(nucc_file)

import os
es_server = os.environ.get('ESDB_PORT_9200_TCP_ADDR') or '127.0.0.1'
es_port = os.environ.get('ESDB_PORT_9200_TCP_PORT') or '9200'


es = Elasticsearch([
	'%s:%s'%(es_server, es_port)  #point this to your elasticsearch service endpoint
	]) 

start = time.time()

print "start at", start
#invoke ES bulk loader using the iterator
helpers.bulk(es, iter_nppes_data(nppes_file,nucc_dict,convert_to_json))
print "total time - seconds", time.time()-start


