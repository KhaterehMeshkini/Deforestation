# Deforestation Analysis Tool
A Python implementation for deforestation analysis on satellite imagery data. This tool processes NDVI and BSI data, integrates them with a WebGIS-provided mask (e.g., Schianti Map), and outputs a change map representing the year of detected changes and their probabilities.

# Input Integration:  
Combines NDVI (Normalized Difference Vegetation Index) and BSI (Bare Soil Index) satellite data with a mask to focus on specific regions of interest.
# Efficient Processing  
Implements parallel processing for computational efficiency.
# Data Handling:
Interpolates missing monthly data for NDVI and BSI, ensuring a complete time series.
Averages values if multiple samples exist within a month.
Skips interpolation if sufficient monthly data is available.
# Index Fusion: Merges NDVI and BSI into a single fused dataset using their root mean square.
# Change Detection:
Uses the BFAST (Breaks for Additive Season and Trend) algorithm to identify and analyze significant change events.
Outputs a change map:
Band 1: Year of change detected.
Band 2: Probability of change.Deforestation Usage


## Setup
  
git clone https://github.com/yourusername/forest_detection.git  

cd forest_detection

pip install -r requirements.txt

## Configuration File (config.ini)

[GENERAL]  

The code requires a config.ini file to specify the parameters for analysis. Below are the details of each section:  

start_year:	The first year of the time series. example 2018  

end_year:	The last year of the time series.	example 2019  

freq:	Temporal frequency (e.g., monthly = 12).	example 12  

verbosity:	Logging verbosity level (0, 1, 2).	example 1

[INPUT]  

ndvi_path	Path to the NDVI GeoTIFF file.	/path/to/NDVI_file.tif  

bsi_path	Path to the BSI GeoTIFF file.	/path/to/BSI_file.tif  

mask_path	Path to the mask GeoTIFF file.	/path/to/mask_file.tif  


[OUTPUT]  

output_directory:	Directory to save output files.	/path/to/output

## USAGE

Set up the config.ini file
Update the configuration file with appropriate paths and parameters.

Run the Script
Use the following command to execute the tool:
python main.py -c config.ini