#!/bin/bash

if [ ! -e "/data/npidata_20050523-20150412.csv" ]
then
    cd /data
    wget http://nppes.viva-it.com/NPPES_Data_Dissemination_April_2015.zip
    unzip NPPES_Data_Dissemination_April_2015.zip
    rm NPPES_Data_Dissemination_April_2015.zip
fi

if [ ! -e "/data/nucc_taxonomy_150.csv" ]
then
    cd /data
    wget http://www.nucc.org/images/stories/CSV/nucc_taxonomy_150.csv
fi

python /code/nppes_fhir_demo/load_nppes_bulk.py \
	/data/npidata_20050523-20150412.csv \
	/data/nucc_taxonomy_150.csv
