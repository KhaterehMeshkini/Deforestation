import os
import numpy as np
import rasterio
import configparser
from datetime import datetime
from joblib import Parallel, cpu_count, delayed
import filemanager as fm
import custom_bfast as bfast
import post_processing as pp



# Parallel BFAST processing
def run_bfast_parallel(par_mngr, ts_2D, dates, freq, verbosity=0):
    step = max(len(ts_2D) // cpu_count(), 100)
    parallel_range = range(0, len(ts_2D), step)
    results = list(
        zip(
            *par_mngr(
                delayed(bfast.bfast_cci)(
                    ts_2D[start: start + step].T,
                    dates,
                    h=(freq / 2) / (ts_2D.shape[1]),
                    verbosity=verbosity,
                )
                for start in parallel_range
            )
        )
    )
    return np.concatenate(results[0], axis=0), np.concatenate(results[1], axis=0)



# Extract dates from TIFF metadata
def extract_dates_from_tiff_band_descriptions(tiff_file_path):
    with rasterio.open(tiff_file_path) as src:
        descriptions = src.descriptions
    dates = [
        datetime.strptime(desc.split("_")[0], "%Y-%m-%d")
        for desc in descriptions
        if desc
    ]
    return dates

# Interpolation and Fusion
def interpolate_time_series(pixel_data, dates_per_year):
    def interpolate_for_year(data, dates):
        # Create an array of months corresponding to the dates
        months = np.array([d.month for d in dates])

        # Initialize an array to store the interpolated data for each month
        interpolated = np.zeros(12)
        valid_months = np.zeros(12, dtype=bool)

        # Loop through each month (1-12)
        for month in range(1, 13):
            # Find the indices of the samples for the current month
            valid_indices = (months == month) & ~np.isnan(data)

            # If there are samples for the current month
            if valid_indices.any():
                # If multiple samples, take the average
                interpolated[month - 1] = np.nanmean(data[valid_indices])
                valid_months[month - 1] = True
            else:
                # If no sample for the current month, mark it as missing
                valid_months[month - 1] = False

        # If there are any missing months, perform interpolation
        if not np.all(valid_months):
            # Get the months with valid data
            valid_months_indices = np.where(valid_months)[0]
            valid_data = interpolated[valid_months_indices]

            # Interpolate over the missing months
            missing_months_indices = np.where(~valid_months)[0]
            if len(valid_months_indices) > 1:  # Only interpolate if there are enough valid months
                interpolated[missing_months_indices] = np.interp(
                    missing_months_indices, valid_months_indices, valid_data
                )
            else:
                # If not enough valid months, fill with NaN or any default value
                interpolated[missing_months_indices] = np.nan

        return interpolated

    # Process each year's data and concatenate the interpolated data
    interpolated_data = []
    offset = 0
    for year_dates in dates_per_year:
        year_data = pixel_data[offset : offset + len(year_dates)]
        interpolated_data.append(interpolate_for_year(year_data, year_dates))
        offset += len(year_dates)

    return np.concatenate(interpolated_data)


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

