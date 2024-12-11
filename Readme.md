AIPC  
kind: component  
ai: remote sensing  
domain: generic 


## Deforestration 

This repository contains a Python implementation for forest detction analysis on satellite imagery data. The script processes NDVI and BSI data, performs interpolation, and detects change events using BFAST.

## Features
- Parallel processing for efficiency
- Interpolation of missing data
- Fusion of NDVI and BSI indices
- Change detection using BFAST

## Usage
Tool usage documentation here.

## Setup
  
git clone https://github.com/yourusername/forest_detection.git  

cd forest_detection

pip install -r requirements.txt

## Configuration File (config.ini)


The code requires a config.ini file to specify the parameters for analysis. Below are the details of each section:  
'''
[GENERAL]  

start_year:	The first year of the time series.  

end_year:	The last year of the time series.	  

freq:	Temporal frequency (e.g., monthly = 12).	

verbosity:	Logging verbosity level (0, 1, 2).	

[INPUT]  

ndvi_path	Path to the NDVI GeoTIFF file.	/path/to/NDVI_file.tif  

bsi_path	Path to the BSI GeoTIFF file.	/path/to/BSI_file.tif  

mask_path	Path to the mask GeoTIFF file.	/path/to/mask_file.tif  


[OUTPUT]  

output_directory:	Directory to save output files.	/path/to/output
'''
