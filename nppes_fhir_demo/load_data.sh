#!/bin/bash

if [ ! -e "/data/npidata_20050523-20150412.csv" ]
then
    cd /tmp
    wget http://nppes.viva-it.com/NPPES_Data_Dissemination_April_2015.zip
    unzip NPPES_Data_Dissemination_April_2015.zip
    rm NPPES_Data_Dissemination_April_2015.zip
    mv npidata_20050523-20150412.csv /data
fi

python /code/nppes_fhir_demo/load_nppes_bulk.py \
	/data/npidata_20050523-20150412.csv \
	/code/NPPES_data/nucc_taxonomy_150.csv
