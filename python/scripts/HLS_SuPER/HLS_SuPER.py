# -*- coding: utf-8 -*-
"""
===============================================================================
HLS Subsetting, Processing, and Exporting Reformatted Data Prep Script                         
Authors: Cole Krehbiel, Mahsa Jami, and Erik Bolch
Contact: lpdaac@usgs.gov
Last Updated: 2024-09-18  
===============================================================================
"""

# Possible Future Improvements:
# TODO Improve CF-1.6 NetCDF Compliance
# TODO Improve behavior around deletion of cogs when a netcdf is requested
# TODO Add ZARR as output option

import argparse
import sys
import os
import shutil
import logging
import time
import json

import earthaccess
from shapely.geometry import polygon, box
from shapely.geometry.polygon import orient
import geopandas as gpd
from datetime import datetime as dt
import dask.distributed

from HLS_Su import hls_search
from HLS_PER import process_granule, create_timeseries_dataset


def parse_arguments():
    """
    Function to parse command line input arguments.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Performs Spatial/Temporal/Band Subsetting, Processing, and Customized Exporting for HLS V2.0 files",
    )

    # roi: Region of interest as shapefile, geojson, or comma separated LL Lon, LL Lat, UR Lon, UR Lat
    parser.add_argument(
        "-roi",
        type=str,
        required=True,
        help="(Required) Region of Interest (ROI) for spatial subset. \
                        Valid inputs are: (1) a geojson or shapefile (absolute path to file required if not in same directory as this script), or \
                        (2) bounding box coordinates: 'LowerLeft_lon,LowerLeft_lat,UpperRight_lon,UpperRight_lat'\
                        NOTE: Negative coordinates MUST be written in single quotation marks '-120,43,-118,48'\
                        NOTE 2: If providing an absolute path with spaces in directory names, please use double quotation marks "
        " ",
    )

    # dir: Directory to save the files to
    parser.add_argument(
        "-dir",
        required=False,
        help="Directory to export output HLS files to.",
        default=os.getcwd(),
    )

    # start: Start Date
    parser.add_argument(
        "-start",
        required=False,
        help="Start date for time period of interest: valid format is yyyy-mm-dd (e.g. 2020-10-20).",
        default="2014-04-03",
    )

    # end: End Date
    parser.add_argument(
        "-end",
        required=False,
        help="Start date for time period of interest: valid format is yyyy-mm-dd (e.g. 2022-10-24).",
        default=dt.today().strftime("%Y-%m-%d"),
    )

    # prod: product(s) desired to be downloaded
    parser.add_argument(
        "-prod",
        choices=["HLSS30", "HLSL30", "both"],
        required=False,
        help="Desired product(s) to be subset and processed.",
        default="both",
    )

    # layers: layers desired to be processed within the products selected
    parser.add_argument(
        "-bands",
        required=False,
        help="Desired layers to be processed. Valid inputs are ALL, COASTAL-AEROSOL, BLUE, GREEN, RED, RED-EDGE1, RED-EDGE2, RED-EDGE3, NIR1, SWIR1, SWIR2, CIRRUS, TIR1, TIR2, WATER-VAPOR, FMASK, VZA, VAA, SZA, SAA. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names.",
        default="ALL",
    )

    # cc: maximum cloud cover (%) allowed to be returned (by scene)
    parser.add_argument(
        "-cc",
        required=False,
        help="Maximum (scene-level) cloud cover (percent) allowed for returned observations (e.g. 35). Valid range: 0 to 100 (integers only)",
        default="100",
    )

    # qf: quality filter flag: filter out poor quality data yes/no
    parser.add_argument(
        "-qf",
        choices=["True", "False"],
        required=False,
        help="Flag to quality filter before exporting output files (see README for quality filtering performed).",
        default="True",
    )

    # sf: scale factor flag: Scale data or leave unscaled yes/no
    parser.add_argument(
        "-scale",
        choices=["True", "False"],
        required=False,
        help="Flag to apply scale factor to layers before exporting output files. This is generally unecessary as most applications will scale automatically.",
        default="False",
    )

    # of: output file format
    parser.add_argument(
        "-of",
        choices=["COG", "NC4", "ZARR"],
        required=False,
        help="Define the desired output file format",
        default="COG",
    )

    # chunksize: chunk size for processing with dask
    parser.add_argument(
        "-cs",
        type=str,
        help="Chunksize for processing scenes with dask in format 'band,x,y'. This is used to provide chunk_size argument to rioxarray.open_rasterio to improve processing speed.\
            For example: '1,512,512' (native hls chunk size) provides better performance for ROIs that fall within a single scene, while '1,3600,3600' (full HLS scene) provides better performance for \
            larger ROIs that span multiple scenes. The default is '1,512,512', but this can lead to a very large task list for large ROIs.",
        default="1,512,512",
    )

    # logfile: Optional logfile path
    parser.add_argument(
        "-logfile",
        required=False,
        help="Optional path to output logfile. If not provided, logging will only be to the console.",
    )

    return parser.parse_args()

def ensure_ccw(geom):
    """
    Ensure the exterior ring of the polygon is counterclockwise.
    """
    if geom.exterior.is_ccw:
        return geom  # Already counterclockwise
    else:
        return orient(geom, sign=1.0)  # Make it counterclockwise
    
def format_roi(roi):
    """
    Determines if submitted ROI is a file or bbox coordinates.

    If a file, opens a GeoJSON or shapefile and creates a list of polygon vertices in the correct order. If the file has multiple polygons it will use a unary union convex hull of the external bounds.

    If bbox coordinates, creates a geodataframe with a single Polygon geometry.

    Returns a geopandas dataframe for clipping and a list of vertices for searching.
    """
    if os.path.isfile(roi):  # and roi.endswith(("geojson", "shp")):
        print(roi)
        try:
            # Open ROI if file
            roi = gpd.read_file(roi)
            if len(roi) > 1:
                # Merge all Polygon geometries and create external boundary
                logging.info(
                    "Multiple polygons detected. Creating single geometry of external coordinates."
                )
                single_geometry = roi.unary_union.convex_hull
                roi = gpd.GeoDataFrame(geometry=[single_geometry], crs=roi.crs)
                logging.info(roi)
            # Check if ROI is in Geographic CRS, if not, convert to it
            if roi.crs.is_geographic:
                roi['geometry'] = roi['geometry'].apply(ensure_ccw)
                # List Vertices in correct order for search
                vertices_list = list(roi.geometry[0].exterior.coords)

            else:
                roi_geographic = roi.to_crs("EPSG:4326")
                logging.info(
                    "Note: ROI submitted is being converted to Geographic CRS (EPSG:4326)"
                )
                roi['geometry'] = roi['geometry'].apply(ensure_ccw)
                vertices_list = list(roi_geographic.geometry[0].exterior.coords)
        except (FileNotFoundError, ValueError):
            sys.exit(
                f"The GeoJSON/shapefile is either not valid or could not be found.\nPlease double check the name and provide the absolute path to the file or make sure that it is located in {os.getcwd()}"
            )
    else:
        # If bbox coordinates are submitted
        bbox = tuple(map(float, roi.strip("'\"").split(",")))
        print(bbox)

        # Convert bbox to a geodataframe for clipping
        roi = gpd.GeoDataFrame(geometry=[box(*bbox)], crs="EPSG:4326")

        vertices_list = list(roi.geometry[0].exterior.coords)

    return (roi, vertices_list)


def format_dates(start, end):
    # Strip Quotes
    start = start.strip("'").strip('"')
    end = end.strip("'").strip('"')
    # Convert to datetime
    try:
        start = dt.strptime(start, "%Y-%m-%d")
        end = dt.strptime(end, "%Y-%m-%d")
    except ValueError:
        sys.exit(
            "A date format is not valid. The valid format is ISO 8601: YYYY-MM-DD (e.g. 2020-10-20)"
        )
    if start > end:
        sys.exit(
            f"The Start Date requested: {start} is after the End Date Requested: {end}."
        )
    else:
        dates = (start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    return dates


def format_cloud_cover(cc):
    try:
        cc = int(cc.strip("'").strip('"'))
    except ValueError:
        sys.exit(
            f"{cc} is not a valid input for filtering by cloud cover (e.g. 35). Valid range: 0 to 100 (integers only)"
        )

    # Validate that cc is in the valid range (0-100)
    if cc < 0 or cc > 100:
        sys.exit(
            f"{cc} is not a valid input option for filtering by cloud cover (e.g. 35). Valid range: 0 to 100 (integers only)"
        )
    return cc


def str_to_bool(value):
    """
    Converts a string to a boolean.
    Accepts 'True', 'true', '1' as True.
    Accepts 'False', 'false', '0' as False.
    """
    if isinstance(value, str):
        if value.lower() in ("true", "1"):
            return True
        elif value.lower() in ("false", "0"):
            return False
    raise ValueError(f"Cannot convert {value} to boolean.")


def create_band_dict(prod, bands):
    """
    Creates a dictionary of bands and common band names for each collection requested.
    """
    shortname = {"HLSS30": "HLSS30.v2.0", "HLSL30": "HLSL30.v2.0"}

    # Create a dictionary with product name and shortname
    if prod == "both":
        prods = shortname
    else:
        prods = {prod: shortname[prod]}

    # Strip spacing, quotes, make all upper case and create a list
    bands = bands.strip(" ").strip("'").strip('"').upper()
    band_list = bands.split(",")

    # Create a LUT dict including the HLS product bands mapped to names
    lut = {
        "HLSS30": {
            "COASTAL-AEROSOL": "B01",
            "BLUE": "B02",
            "GREEN": "B03",
            "RED": "B04",
            "RED-EDGE1": "B05",
            "RED-EDGE2": "B06",
            "RED-EDGE3": "B07",
            "NIR-Broad": "B08",
            "NIR1": "B8A",
            "WATER-VAPOR": "B09",
            "CIRRUS": "B10",
            "SWIR1": "B11",
            "SWIR2": "B12",
            "FMASK": "Fmask",
            "VZA": "VZA",
            "VAA": "VAA",
            "SZA": "SZA",
            "SAA": "SAA",
        },
        "HLSL30": {
            "COASTAL-AEROSOL": "B01",
            "BLUE": "B02",
            "GREEN": "B03",
            "RED": "B04",
            "NIR1": "B05",
            "SWIR1": "B06",
            "SWIR2": "B07",
            "CIRRUS": "B09",
            "TIR1": "B10",
            "TIR2": "B11",
            "FMASK": "Fmask",
            "VZA": "VZA",
            "VAA": "VAA",
            "SZA": "SZA",
            "SAA": "SAA",
        },
    }

    # List of all available/acceptable band names
    all_bands = [
        "ALL",
        "COASTAL-AEROSOL",
        "BLUE",
        "GREEN",
        "RED",
        "RED-EDGE1",
        "RED-EDGE2",
        "RED-EDGE3",
        "NIR1",
        "SWIR1",
        "SWIR2",
        "CIRRUS",
        "TIR1",
        "TIR2",
        "WATER-VAPOR",
        "FMASK",
        "VZA",
        "VAA",
        "SZA",
        "SAA",
    ]

    # Validate that bands are named correctly
    for b in band_list:
        if b not in all_bands:
            sys.exit(
                f"Band: {b} is not a valid input option. Valid inputs are {all_bands}. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names."
            )

    # Set up a dictionary of band names and numbers by product
    band_dict = {}
    for p in prods:
        band_dict[p] = {}
        for b in band_list:
            if b == "ALL":
                band_dict[p] = lut[p]
            else:
                try:
                    band_dict[p][b] = lut[p][b]
                except ValueError:
                    print(f"Product {p} does not contain band {b}")
    return band_dict


def format_chunksize(chunksize):
    """
    Converts comma-separated chunksize string to dictionary.
    """
    keys = ["band", "x", "y"]
    values = list(map(int, chunksize.strip("'\"").split(",")))

    if len(values) != len(keys):
        raise ValueError(
            "Chunksize must provide band, x and y (3) values separated by commas."
        )

    return dict(zip(keys, values))


def confirm_action(prompt):
    """
    Prompts the user to confirm an action.
    """
    while True:
        response = input(prompt).lower()
        if response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def setup_dask_environment():
    """
    Passes RIO environment variables to dask workers for authentication.
    """
    import os
    import rasterio

    global env
    env = rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_COOKIEFILE=os.path.expanduser("~/cookies.txt"),
        GDAL_HTTP_COOKIEJAR=os.path.expanduser("~/cookies.txt"),
        GDAL_HTTP_MAX_RETRY="10",
        GDAL_HTTP_RETRY_DELAY="0.5",
    )
    env.__enter__()


def main():
    """
    Main function to run the HLS SuPER script.
    """

    # Parse arguments
    args = parse_arguments()

    # Configure logging
    log_handlers = [logging.StreamHandler(sys.stdout)]
    if args.logfile:
        log_handlers.append(logging.FileHandler(args.logfile))

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(asctime)s ||| %(message)s",
        handlers=log_handlers,
    )

    # Handle Login Credentials with earthaccess
    earthaccess.login(persist=True)

    # Start Log
    logging.info("HLS SuPER script started")

    # Format ROI
    roi, vl = format_roi(args.roi)
    logging.info("Region of Interest formatted successfully")

    # Set Output Directory
    if args.dir is not None:
        output_dir = os.path.normpath(args.dir.strip("'").strip('"')) + os.sep
    else:
        # Defaults to the current directory
        output_dir = os.getcwd() + os.sep

    logging.info(f"Output directory set to: {output_dir}")

    # Format/Validate Dates
    dates = format_dates(args.start, args.end)
    logging.info(f"Date Parameters: {dates}")

    # Create Product/Band Dictionary
    band_dict = create_band_dict(args.prod, args.bands)
    logging.info(f"Products/Bands Selected: {band_dict}")

    # Format Cloud Cover
    cc = format_cloud_cover(args.cc)
    logging.info(f"Cloud Cover Filter <= {cc}")

    # Quality Filtering
    qf = str_to_bool(args.qf)
    logging.info(f"Quality Filtering: {qf}")

    # Scale Factor
    scale = str_to_bool(args.scale)
    logging.info(f"Apply Scale Factor: {scale}")

    # Chunk Size
    chunk_size = format_chunksize(args.cs)
    logging.info(f"Chunk Size: {chunk_size}")

    # Output File Type
    if args.of not in ["COG", "NC4"]:
        sys.exit(
            f"Output format {args.of} is not a valid output format. Please choose from 'COG', 'NC4'."
        )

    logging.info(f"Output format: {args.of}")

    # Search for Data and Save Results
    results_urls_file = os.path.join(output_dir, "hls_super_results_urls.json")
    use_existing_file = False

    if os.path.isfile(results_urls_file):
        logging.info(f"Results url list already exists in {output_dir}.")
        # Confirm if user wants to use existing file.
        if confirm_action(
            f"Do you want to use the existing results file ({results_urls_file})? (y/n)"
        ):
            use_existing_file = True

        else:
            if not confirm_action(
                "Do you want to overwrite the existing results file? (y/n)"
            ):
                sys.exit(
                    f"Processing aborted. Please move, rename, or remove existing file: {results_urls_file}."
                )

    if use_existing_file:
        logging.info("Using existing results file.")
        with open(results_urls_file, "r") as file:
            results_urls = json.load(file)

    else:
        logging.info("Searching for data...")
        results_urls = hls_search(
            roi=vl, band_dict=band_dict, dates=dates, cloud_cover=cc
        )
        logging.info(f"Writing search results to {results_urls_file}")
        with open(results_urls_file, "w") as file:
            json.dump(results_urls, file)

    total_assets = sum(len(sublist) for sublist in results_urls)

    if cc:
        logging.info(
            f"{len(results_urls)} granules remain after cloud filtering. {total_assets} assets will be processed."
        )
    else:
        logging.info(f"{total_assets} assets will be processed.")

    # Confirm Processing
    if not confirm_action("Do you want to proceed with processing? (y/n)"):
        sys.exit("Processing aborted.")

    # Initialize Dask Cluster
    client = dask.distributed.Client()

    # Setup Dask Environment (GDAL Configs)
    client.run(setup_dask_environment)

    logging.info(
        f"Dask environment setup successfully. View dashboard: {client.dashboard_link}."
    )

    # Scatter Results Results url
    client.scatter(results_urls)

    # If NC4, create a temporary directory to store COGs
    if args.of == "NC4":
        cog_dir = os.path.join(output_dir, "temp")
        if not os.path.exists(cog_dir):
            os.makedirs(cog_dir, exist_ok=True)
        else:
            if not confirm_action(
                "Temporary directory to store COGs already exists. Use these files to create NC4 outputs? (y/n)"
            ):
                sys.exit(
                    f"Processing aborted. Please remove existing directory: {cog_dir}."
                )

    else:
        cog_dir = output_dir

    # Process Granules
    start_time = time.time()
    logging.info("Processing...")
    tasks = [
        dask.delayed(process_granule)(
            granule_url,
            roi=roi,
            quality_filter=qf,
            scale=scale,
            output_dir=cog_dir,
            band_dict=band_dict,
            bit_nums=[0, 1, 2, 3, 4, 5],
            chunk_size=chunk_size,
        )
        for granule_url in results_urls
    ]
    dask.compute(*tasks)

    # Create Timeseries Dataset if NC4
    if args.of == "NC4":
        logging.info("Creating timeseries dataset...")
        create_timeseries_dataset(cog_dir, output_type=args.of, output_dir=output_dir)

    # Close Dask Client
    client.close()

    # Remove Temporary COGs if NC4
    if args.of == "NC4":
        logging.info("Timeseries Dataset Created. Removing Temporary Files...")
        shutil.rmtree(cog_dir)

    # End Timer
    total_time = time.time() - start_time
    logging.info(
        f"Processing complete. Total time: {round(total_time,2)}s, "
    )


if __name__ == "__main__":
    main()
