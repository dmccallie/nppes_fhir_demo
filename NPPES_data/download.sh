#!/bin/sh

wget http://www.nucc.org/images/stories/CSV/nucc_taxonomy_150.csv
#dpm - 15Aug2018 - changed to most recent data file
wget http://download.cms.gov/nppes/NPPES_Data_Dissemination_August_2018.zip
#wget http://nppes.viva-it.com/NPPES_Data_Dissemination_May_2015.zip
#load_nppes_bulk can now read directly from the zip file
#unzip NPPES_Data_Dissemination_April_2015.zip
