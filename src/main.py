import os
import numpy as np
import rasterio
import configparser
from datetime import datetime
from joblib import Parallel, cpu_count, delayed
import filemanager as fm
import custom_bfast as bfast
import post_processing as pp
from utils import run_bfast_parallel, extract_dates_from_tiff_band_descriptions, interpolate_time_series


# Main function
def main():
    
    # Load configuration
    config = configparser.ConfigParser()
    config.read("config.ini")
    ndvi_path = config["Paths"]["NDVI"]
    bsi_path = config["Paths"]["BSI"]
    mask_path = config["Paths"]["Mask"]
    output_path = config["Paths"]["Output"]
    startyear = int(config["Settings"]["StartYear"])
    endyear = int(config["Settings"]["EndYear"])
    freq = int(config["Settings"]["Frequency"])

    # Read data
    ndvi_data = fm.readGeoTIFFD(ndvi_path, metadata=True)[0]
    bsi_data = fm.readGeoTIFFD(bsi_path, metadata=True)[0]
    mask = fm.readGeoTIFF(mask_path, metadata=True)[0]
    ndvi_dates = extract_dates_from_tiff_band_descriptions(ndvi_path)
    clip_mask, newtr, projection = fm.clipGeoTIFF(ndvi_path, mask_path)
    geotransform = fm.readGeoTIFFD(ndvi_path, metadata=True)
    geotransform = geotransform[1]



    # Filter dates by year range
    years = range(startyear, endyear + 1)
    nyear = endyear - startyear
    dates_per_year = [[d for d in ndvi_dates if d.year == year] for year in years]

    # Mask and interpolate data
    ndvi = np.where(clip_mask[:,:,np.newaxis] == 0, np.nan, ndvi_data)
    bsi = np.where(clip_mask[:,:,np.newaxis] == 0, np.nan, bsi_data)


    height, width, _ = ndvi.shape
    interpolated_data = np.zeros((height, width, len(years) * 12))

    for i in range(height):
        for j in range(width):
            interpolated_ndvi = interpolate_time_series(ndvi[i, j, :], dates_per_year)
            interpolated_bsi = interpolate_time_series(bsi[i, j, :], dates_per_year)
            interpolated_data[i, j, :] = np.sqrt((interpolated_ndvi**2 + interpolated_bsi**2) / 2)

    # Run BFAST
    fused_reshaped = interpolated_data.reshape(-1, len(years) * 12)
    years_np = np.arange(startyear, endyear+1)
    with Parallel(n_jobs=-1) as parallel:
        dates = bfast.r_style_interval(
            (startyear, 1), (startyear + nyear, 365), freq
        ).reshape(fused_reshaped.shape[1], 1)
        breaks, confidence = run_bfast_parallel(
            parallel, fused_reshaped, dates, freq
        )


    # Process results
    changemaps = breaks // freq
    accuracymaps = confidence
    changemaps = changemaps.reshape(height, width)
    accuracymaps = accuracymaps.reshape(height, width)

    changemaps_year = np.zeros_like(changemaps, dtype = int)
    for i, year in enumerate(years_np):
        changemaps_year[changemaps == i] = year

    # Remove isolated pixels
    updated_change_array, updated_probability_array = pp.remove_isolated_pixels(changemaps_year, accuracymaps)

    # Fill gaps and update probabilities
    final_change_array, final_probability_array = pp.fill_small_holes_and_update_probabilities(updated_change_array, updated_probability_array) 

    final_change_array = final_change_array.astype(float)
    final_probability_array = final_probability_array.astype(float)
    final_change_array[final_change_array ==0 ] = np.nan
    final_probability_array[final_probability_array ==0 ] = np.nan


    # Save output 
    filename = "CD_" + str(startyear) + "_" + str(endyear) + ".tif"
    output_filename = fm.joinpath(output_path, filename)
    print(final_change_array)
    

    fm.writeGeoTIFFD(output_filename, np.stack([final_change_array, final_probability_array], axis=-1), geotransform, projection, nodata=-1) 

    print("Processing complete!")   


if __name__ == "__main__":
    main()             

