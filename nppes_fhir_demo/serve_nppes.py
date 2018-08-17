#dpm 15Aug2018 - ported to python3

from flask import Flask, jsonify, render_template, request, Response
import elasticsearch
import json
import urllib, urllib.parse
from collections import OrderedDict #use ordered dictionary to preserve JSON order
from uuid import uuid4

#creates WSGI entry point for gunicorn
app = Flask(__name__)
es = ""
 

#starting point for FHIR Practivtioner demo - yields the search form
@app.route('/nppes_fhir')
def nppes_fhir():
	return render_template('fhir_index.html') 


#FHIR Practitioner by /npi
@app.route('/nppes/Practitioner/<npi>', methods=['GET'])
def handle_npi_lookup(npi):
	#query was for a specific provider
	#return the FHIR Practitioner record
	#npi 			= request.args.get('_id', '').strip()
	query = "npi:" + npi
	try:
		es_reply = es.search(index='nppes', doc_type="provider", q=query)
	except:
		print("FAILED to query ES ")
		raise
	if (es_reply and (es_reply['hits']['total'] == 1)):

		hits = es_reply['hits']['hits']

		prac = build_fhir_Practitioner(hits[0]['_source'])
		return Response(json.dumps(prac, indent=2, separators=(',', ': ')), mimetype="application/json")

	else:
		return jsonify("")



#FHIR Practitioner search service - returns FHIR Bundle of matching Pracitioner matches
@app.route('/nppes/Practitioner', methods=['GET'])
def fhir_lookup():

	#only supports these FHIR fields for demo
	anystring		= request.args.get('anystring', '').strip() #dpm - added for demo of open-ended query approach
	npi 			= request.args.get('_id', '').strip()
	family        	= request.args.get('family', '').strip()
	given         	= request.args.get('given', '').strip()
	address       	= request.args.get('address', '').strip()
	qualification 	= request.args.get('qualification', '').strip()
	#specialty_code  = request.args.get('specialty').strip() #for now, this gets IGNORED!
	specialty_text  = request.args.get('specialty:text', '').strip() #FHIR uses :text for text search on tokens
	page            = request.args.get('page', 1, type=int) #which page to start with
	count           = request.args.get('_count', 15, type=int) #results per page

	#calculate starting point
	startfrom = (page-1) * count

	queryText = ""
	wildcard = "*"  #lucene wildcard is applied to some of the search parameters

	#if 'anystring' is not empty, do the whole query with terms contained in the string
	#this means no special weighting of lastname, etc
	#it's an experiment

	if len(anystring)>0:
		#strip periods and dashes
		anystring = anystring.replace(".","").replace("-","")
		#split into words to form query terms - wildcard them all for now
		for term in anystring.split():
			queryText += (term + wildcard + " ")
	
	else:

		#build a Lucene query string - see Lucene documentation for syntax
		if family:        queryText += "lastname:"     + family    + wildcard + "^4" + " "
		if given:         queryText += "firstname:"    + given     + wildcard + " "
		if address:
			#apply wildcard to each part of whatever user entered (street, city, state code)
			for term in address.split():       
				queryText += "full_address:" + term + wildcard + " "
		if qualification: queryText += "credential:"   + qualification        + " "
		if specialty_text:
			specText = ""
			#allow for either spec_1 OR spec_2 to qualify.  Everything else is an AND
			for term in specialty_text.split():
				specText += "spec_1:" + term + wildcard + " OR " + "spec_2:" + term + wildcard + " OR "

			queryText +=  " (" + specText[:-3] + ")"

	print ("generated Lucene query = ", queryText) #debug
	
	#invoke ElasticSearch using the "lucene query mode"
	try:
		es_reply = es.search(index='nppes', default_operator="AND", size=count, from_=startfrom, q=queryText)
	except:
		print ("FAILED to query ES ")
		raise
	#print "es reply = ", es_reply
	
	data = ""
	total = es_reply['hits']['total']  #total matches
	time = es_reply['took']		#milliseconds of ES time

	#get root of results
	hits = es_reply['hits']['hits']
	providers = []
	if (len(hits) > 0):
		done = False
		for h in hits:
			src = h['_source']
			a_doc = build_fhir_Practitioner(src)
			providers.append(a_doc)
	else:
		done = True

	#calculate URLs for next and prev page.
	request_params = request.args.copy()

	if ((not done) and len(providers) >= count):
		request_params['page'] = page + 1
		nextUrl = request.base_url + "?" + urllib.parse.urlencode(request_params)
	else:
		nextUrl = ''

	if page > 1:
		request_params['page'] = page - 1
		prevUrl = request.base_url + "?" + urllib.parse.urlencode(request_params)
	else:
		prevUrl = ''
	

	the_bundle = build_fhir_bundle(total, time, providers, nextUrl, prevUrl, startfrom)
	
	#use Flask Response class instead of jsonify() in order to control JSON use of OrderedDict
	return Response(json.dumps(the_bundle, indent=2, separators=(',', ': ')), mimetype="application/json")

#utility routines
def build_fhir_Practitioner(es_provider_doc):
	#convert the results of an ES match to FHIR Practitioner record format
	#build with python structures and then JSONify
	#this is a total hack approach.  proof of concept with lots of gaps!

	prac = OrderedDict()  #allows preservation of dictionary names, for easier debugging
	#note that OrderedDict literal inits are ugly, e.g.:  OrderedDict( [ (tuple), (tuple) ] )

	prac['resourceType'] = "Practitioner"
	prac['id'] = es_provider_doc.get('npi',"0")
	prac['identifier'] = [OrderedDict([	
			('use', "official"),
			('system', "http://hl7.org/fhir/sid/us-NPI????"),
			('value', es_provider_doc.get('npi',"0")),
		])]
	prac['name'] = OrderedDict([
			("use", "official"),
			("family", [ es_provider_doc.get('lastname')]),
			("given", [ es_provider_doc.get('firstname')]),
			("suffix", [ es_provider_doc.get('credential')])
		])
	prac['gender'] = "unknown"
	address_line = es_provider_doc.get('mail_address_1')
	if es_provider_doc.get('mail_address_2'):
		address_line += "<br>" + es_provider_doc.get('mail_address_2')
	prac['address'] = OrderedDict([ 
			("use", "work"),
			("line", [ address_line ]),
			("city", es_provider_doc.get('city')),
			("state", es_provider_doc.get('state_abbrev')),
			("country", "USA")
		])
	prac['telecom'] = [ OrderedDict([
			("extension", [
				{
					"url" : "http://hl7.org/fhir/StructureDefinition/us-core-direct",
					"valueBoolean" : True
				}
			]),
			("system", "email"),
			("value", es_provider_doc.get('firstname')[0:1] + "." + es_provider_doc.get('lastname') + "@direct.somehist.com"),
			("use", "work")
		])]

	if es_provider_doc.get('spec_1'):
		prac['practitionerRole'] = [{
				"specialty": [
				  {
					"coding": [{
						"system": "http://www.wpc-edi.com/codes/taxonomy",
						"code": "??"
					}],
					"text": es_provider_doc.get('spec_1')
				  }]
			}]
	if es_provider_doc.get('spec_2'):
		prac['practitionerRole'][0]['specialty'].append(
				 {
					"coding": [{
						"system":  "http://www.wpc-edi.com/codes/taxonomy",
						"code": "??"
					}],
					"text": es_provider_doc.get('spec_2')
				 }
			)

	return prac

def build_fhir_bundle(total, time, providers, nextUrl, prevUrl, startfrom):
	#wrap the results into a FHIR bundle.  Ugh.

	bundle = OrderedDict()

	#first, some header stuff.
	bundle["resourceType"] = "Bundle"
	bundle["id"] =  str(uuid4()) #not sure why we need this, but GG says so
	bundle["type"] =  "searchset"
	bundle["base"] = "http://davidmccallie.com/nppes"
	bundle["total"] = total

	#set up the pageing links
	bundle["link"] = [
		{
			"relation": "next",
			"url": nextUrl
		},
		{
			"relation" : "prev",
			"url" : prevUrl
		}
	]

	#then, convert each matching practitioner into a entry.resource
	bundle["entry"] = []
	for prov in providers:
		bundle["entry"].append({ "resource" : prov})

	return bundle


#main program here

import os
es_server = os.environ.get('ESDB_PORT_9200_TCP_ADDR') or '127.0.0.1'
es_port = os.environ.get('ESDB_PORT_9200_TCP_PORT') or '9200'

try:
	es = elasticsearch.Elasticsearch([
	'%s:%s'%(es_server, es_port)  #point this to your elasticsearch service endpoint
	]) 
	print ("connected to ES")
except:
	print ("FAILED to connect to ES ")
	raise

#if called locally (without gunicorn) then run on localhost port 5000 for debugging
#otherwise, gunicorn will invoke the "app" entrypoint for WSGI conversation
if __name__ == '__main__':
	app.run(host="127.0.0.1", port=5000, debug=True)
