#dpm - 15Aug2018 - updated to python3
import csv, sys
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import json
import time
import os
import argparse
import zipfile

parser = argparse.ArgumentParser(description='Bulk load NPPES data')
parser.add_argument('npifile', metavar='N', nargs='?', help='Path to NPI data file',
					#defaults to the May zip file - may need to edit this
					#dpm 15Aug2018 - changed to a more recent dissemination
					default="../NPPES_data/NPPES_Data_Dissemination_August_2018.zip")
parser.add_argument('nuccfile', metavar='N', nargs='?', help='Path to NUCC data file',
					default="../NPPES_data/nucc_taxonomy_150.csv")
args = parser.parse_args()

nppes_file = args.npifile #download this 5GB file from CMS!
nucc_file  = args.nuccfile

#this is the reference data used to specificy provider's specialties
def load_taxonomy(nucc):
	nucc_dict = {}
	with open(nucc, encoding='latin-1') as nucc_file:
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
	provider_document['credential'] = row['Provider Credential Text'].replace(".","")
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

	#experiment with an "all" field to allow for a single query line that doesn't require field-by-field query
	provider_document['all'] =	provider_document['firstname']    + " " + \
								provider_document['lastname']     + " " + \
								provider_document['full_address'] + " " + \
								provider_document['credential']   + " " + \
								provider_document['spec_1']       + " " + \
								provider_document['spec_2']       + " " + \
								provider_document['spec_3']

	return provider_document

def convert_to_json(row, nucc_dict):
	#some kind of funky problem with non-ascii strings here
	#trap and reject any records that aren't full ASCII.
	#fix me!
	
	provider_doc = extract_provider(row, nucc_dict)
	try:
		j = json.dumps(provider_doc, ensure_ascii=True)
		#print("Successful json for ", j)
	except Exception:
		print("FAILED convert a provider record to ASCII = ", row['NPI'])
		#print("Unexpected error:", sys.exc_info()[0])
		j = None
	return j

#create a python iterator for ES's bulk load function
def iter_nppes_data(nppes_file, nucc_dict, convert_to_json):
	count = 0
	#extract directly from the zip file
	zipFileInstance = zipfile.ZipFile(nppes_file, mode='r', allowZip64=True)
	for zipInfo in zipFileInstance.infolist():
		#hack - the name can change, so just use the huge CSV. That's the one
		if zipInfo.file_size > 4000000000:
			print("found NPI CSV file = ", zipInfo.filename)
			content = zipFileInstance.open(zipInfo, 'r') #can't use 'rt' anymore
			decoded_content = (line.decode('utf8') for line in content) #funky trick to turn py3 bytes to string
			reader = csv.DictReader(decoded_content)
			for row in reader:
				#print("GOT A ROW = ", row['Provider Last Name (Legal Name)'])
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
							count += 1
							if count % 5000 == 0:
								print("Count: Loaded {} records".format(count))
							yield action
 	

#dpm 16Aug2018 - added explict creation of indexes to optimize for space, etc

def create_index(es_object, index_name):
	created = False
	# index settings
	settings = {
		"settings": {
			"index" : {
				"number_of_shards": 2,  #doesn't work???
				"number_of_replicas": 0,
			},
			"index" : {
				"analysis" : {
					"filter" : {
						"synonym" : {
							"type" : "synonym",
							"synonyms" : [					#some examples, should be in separate file, etc
								"internist => internal",
								"gi => gastroenterology",
								"knife => surgical, surgeon, surgery",
								"obgyn => obstetrics, gynecology",
								"peds => pediatric, pediatrics"
							]
						},
					},
					"analyzer" : {
						"synonym" : {
							"tokenizer" : "standard",
							"filter" : [
								"lowercase", 
							    "synonym"
							]
						},
					},

				},
			},
		},
		"mappings": {
			"provider": {
				#"dynamic": "strict",
				"properties": {
					"npi":              { "type": "text"},
					"firstname":        { "type": "text", "norms": False, "index_options": "freqs" },
					"lastname":         { "type": "text", "norms": False, "index_options": "freqs" },
					"mail_address_1":   { "type": "text", "norms": False, "index_options": "freqs" },
					"mail_address_2":   { "type": "text", "norms": False, "index_options": "freqs" },
					"city":             { "type": "text", "norms": False, "index_options": "freqs" },
					"state_abbrev":     { "type": "text", "norms": False, "index_options": "freqs" },
					"credential":       { "type": "text", "norms": False, "index_options": "freqs" },
					"spec_1":           { "type": "text", "norms": False, "index_options": "freqs", "analyzer" : "synonym" },
					"spec_2":           { "type": "text", "norms": False, "index_options": "freqs", "analyzer" : "synonym" },
					"spec_3":           { "type": "text", "norms": False, "index_options": "freqs", "analyzer" : "synonym" },
					"all":              { "type": "text", "norms": False, "index_options": "freqs", "analyzer" : "synonym" },
				},
			},
			#"_doc": {
			#	"_source": {
			#		"excludes": [
			#			"*.all",  #dpm - this doesn't appear to work, don't know why.
			#		]
			#	}
			#}
		}
	}
	try:
		if es_object.indices.exists(index_name):
			es_object.indices.delete(index=index_name, ignore=400)
			print("Deleted old index")

		# Ignore 400 means to ignore "Index Already Exist" error.
		es_object.indices.create(index=index_name, body=settings)
		print('Created new index at {}'.format(index_name))
		created = True
	except Exception as ex:
		print("index creation exception: ", str(ex))
	finally:
		return created


#main code starts here

if __name__ == '__main__':
	count = 0
	nucc_dict = load_taxonomy(nucc_file)
	es_server = os.environ.get('ESDB_PORT_9200_TCP_ADDR') or '127.0.0.1'
	es_port = os.environ.get('ESDB_PORT_9200_TCP_PORT') or '9200'

	es = Elasticsearch([
	'%s:%s'%(es_server, es_port)  #point this to your elasticsearch service endpoint
	]) 

	start = time.time()
	print ("start at", start)

	create_index(es, index_name='nppes')
	
	#invoke ES bulk loader using the iterator
	helpers.bulk(es, iter_nppes_data(nppes_file,nucc_dict,convert_to_json))

	print ("total time - seconds", time.time()-start)
