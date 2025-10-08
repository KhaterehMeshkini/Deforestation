import numpy as np
from joblib import Parallel, cpu_count, delayed
import filemanager as fm
import custom_bfast as bfast
import rasterio
from datetime import datetime


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
            if len(valid_months_indices) > 5:  # Only interpolate if there are enough valid months
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