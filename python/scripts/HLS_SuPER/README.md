# HLS Subsetting, Processing, and Exporting Reformatted Data Prep Script  

---

## Objective  

NASA's Land Processes Distributed Active Archive Center (LP DAAC) archives and distributes Harmonized Landsat Sentinel-2 (HLS) version 2.0 products in the LP DAAC Cumulus cloud archive as Cloud Optimized GeoTIFFs (COG). the HLS_SuPER.py data prep script is a command line-executable Python script that allows users to submit inputs for their desired spatial (GeoJSON, Shapefile, bounding box) region of interest (ROI), time period of interest, and the specific desired product(s) and bands/layers within the HLS products. The script also includes options for cloud screening observations by a user-defined threshold, quality filtering, applying the scale factor to the data, and users can pick between three output file format options (COG, NC4, ZARR). The inputs provided by the user are submitted into NASA's Common Metadata Repository SpatioTemporal Asset Catalog (CMR-STAC) API endpoint. The script returns a list of links to the HLS observations that intersect the user's input parameters. From there, the cloud-native observations are accessed, clipped to the spatial ROI, [optionally] quality filtered (see section on quality filtering below), [optionally] scaled, and exported in the desired output file format. Each request includes the accompanying metadata, browse, and quality (Fmask) files. If NetCDF-4 or ZARR are selected as the output file format, observations will be stacked into files grouped by HLS tile. This script does not support resampling or reprojection.  

### Available Products  

1. Daily 30 meter (m) global HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance - [HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002)  

2. Daily 30 meter (m) global HLS Landsat 8 Operational Land Imager Surface Reflectance - [HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002)  

> **Note:** On November 2021, this data prep script is updated to processes Version 2.0 daily 30 meter (m) global HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance (HLSS30) data and Version 2.0 daily 30 m global HLS Landsat 8 OLI Surface Reflectance (HLSL30) data.  

---

## Prerequisites  

This tutorial has been tested on Windows and MacOS using the specifications identified below.  

- **Python Version 3.7**  
  - `shapely`  
  - `geopandas`  
  - `gdal`  
  - `rasterio`  
  - `pyproj`  
  - `requests`  
If exporting to `nc4` or `zarr`:  
    - `xarray`  
    - `netCDF4`  
    - `zarr`  

---  

> **Note:** This data prep script relies on the **CMR-STAC** API, which will continue to evolve in order to align with the STAC spec over time. As these changes are released, we will update this script as necessary. If you are encountering an issue with the script, please check out the [CHANGELOG.md](https://git.earthdata.nasa.gov/projects/LPDUR/repos/hls-super-script/browse/CHANGELOG.md) and make sure that you have copied/cloned/downloaded the latest release of this script.  

## Procedures  

To get started, copy/clone/[download](https://git.earthdata.nasa.gov/rest/api/latest/projects/LPDUR/repos/hls-super-script/archive?format=zip) the [HLS-SuPER-Script repo](https://git.earthdata.nasa.gov/projects/LPDUR/repos/hls-super-script/browse). You will need all three of the python scripts downloaded to the same directory on your OS (HLS_Su.py, HLS_PER.py, HLS_SuPER.py).  

### Python Environment Setup  

It is recommended to use [Conda](https://conda.io/docs/), an environment manager, to set up a compatible Python environment. Download Conda for your OS [here](https://www.anaconda.com/download/). Once you have Conda installed, follow the instructions below to successfully setup a Python environment on Windows, MacOS, or Linux.  

Using your preferred command line interface (command prompt, terminal, cmder, etc.) type the following to create a compatible python environment:  

```None
> conda create -n hls -c conda-forge --yes python=3.9 gdal rasterio=1.2 shapely geopandas pyproj requests xarray netcdf4 zarr  
```  

```None
> conda activate hls
````  

> **Note:** If you are having trouble activating your environment, or loading specific packages once you have activated your environment? Try the following: ```conda update conda``` or ```conda update --all```  

If you prefer to not install Conda, the same setup and dependencies can be achieved by using another package manager such as pip and the [requirements.txt file](https://git.earthdata.nasa.gov/projects/LPDUR/repos/hls-super-script/browse/requirements.txt).  

[Additional information](https://conda.io/docs/user-guide/tasks/manage-environments.html) on setting up and managing Conda environments.  

If you continue to have trouble getting a compatible Python environment set up? Contact [LP DAAC User Services](https://lpdaac.usgs.gov/lpdaac-contact-us/).  

### Setting up a netrc File

Netrc files contain remote username/passwords that can only be accessed by the user of that OS (stored in home directory). Here we use a netrc file to store NASA Earthdata Login credentials. If a netrc file is not found when the script is executed, you will be prompted for your NASA Earthdata Login username and password by the script, and a netrc file will be created in your home directory. If you prefer to manually create your own netrc file, download the [.netrc file template](https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse/.netrc), add your credentials, and save to your home directory. A [NASA Earthdata Login Account](https://urs.earthdata.nasa.gov/) is required to download HLS data.  

---

## Script Execution  

 Once you have set up your environment and it has been activated, navigate to the directory containing the downloaded or cloned repo (with HLS_SuPER.py, HLS_Su.py, and HLS_PER.py). At a minimum, the script requires a region of interest (roi).  

```None
> python HLS_SuPER.py -roi <insert geojson, shapefile, or bounding box coordinates here> -dir <insert directory to save the output files to>
```  

> **Note:** The script will first use the inputs provided to find all intersecting HLS files and export the links to a text file. The user will then be prompted with the number of intersecting files and asked if they would like to continue downloading and processing all of the files (y/n). If your request returns hundreds of files for a large area, you may want to consider breaking the request into smaller requests by submitting multiple requests with different spatial/temporal/band subsets.  

### Examples  

#### Region of interest (```-roi```) specified using a geojson file  

```None  
> python HLS_SuPER.py -roi LA_County.geojson  
```  

#### Region of interest (```-roi```) specified using a bounding box and save outputs to specified directory  

```None  
> python HLS_SuPER.py -dir C:\Users\HLS\ -roi '-122.8,42.1,-120.5,43.1'  
```  

> **Note:** The bounding box is a comma-separated string of LL-Lon, LL-Lat, UR-Lon, UR-Lat.  **Also**, if the first value in your bounding box is negative, you **MUST** use *single* quotations around the bounding box string. If you are using MacOS, you may need to use double quotes followed by single quotes ("'-122.8,42.1,-120.5,43.1'")  

## Additional Script Execution Documentation  

To see the full set of command line arguments and how to use them, type the following in the command prompt:  

```None
> python HLS_SuPER.py -h  

usage: HLS_SuPER.py [-h] -roi ROI [-dir DIR] [-start START] [-end END]
                    [-prod {HLSS30,HLSL30,both}] [-bands BANDS] [-cc CC]
                    [-qf {True,False}] [-scale {True,False}]
                    [-of {COG,NC4,ZARR}]  
...
```

### Script Arguments  

#### -roi ROI  

```None
(Required) Region of Interest (ROI) for spatial subset. Valid inputs are: (1) a geojson or shapefile (absolute path to file required if not in same directory as this script), or (2) bounding box coordinates: 'LowerLeft_lon,LowerLeft_lat,UpperRight_lon,UpperRight_lat' NOTE: Negative coordinates MUST be
written in single quotation marks '-120,43,-118,48'.  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48'  
```  

#### -dir DIR  

```None  
Directory to save output HLS files to. (default: <directory that the script is executed from>)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\  
```  

#### -start START  

```None  
Start date for time period of interest: valid format is mm/dd/yyyy (e.g. 10/20/2020). (default: 04/03/2014)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020  
```  

#### -end END  

```None  
Start date for time period of interest: valid format is mm/dd/yyyy (e.g. 10/24/2020). (default: 12/17/2020)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020  
```  

#### -prod {HLSS30,HLSL30,both}  

```None  
Desired product(s) to be subset and processed. (default: both)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both  
```  

#### -bands BANDS  

```None  
Desired layers to be processed. Valid inputs are ALL, COASTAL-AEROSOL, BLUE, GREEN, RED, RED-EDGE1, RED-EDGE2, RED-EDGE3, NIR1, SWIR1, SWIR2, CIRRUS, TIR1, TIR2, WATER-VAPOR, FMASK. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names. (default: ALL)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both -bands RED,GREEN,BLUE,NIR1  
```  

#### -cc CC  

```None  
Maximum cloud cover (percent) allowed for returned observations (e.g. 35). Valid range: 0 to 100 (integers only) (default: 100)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50`  
```  

#### -qf {True,False}  

```None  
Flag to quality filter before exporting output files (see section below for quality filtering performed). (default: True)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True  
```  

#### -scale {True,False}  

```None  
Flag to apply scale factor to layers before exporting output files. (default: True)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True -scale False  
```

#### -of {COG,NC4,ZARR}  

```None  
Define the desired output file format (default: COG)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 06/02/2020 -end 10/24/2020 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True -scale False -of NC4  
```  

### Quality Filtering  

If quality filtering is set to True (default), the following quality filtering will be used:  

- Cloud == 0 (No Cloud)  
- Cloud shadow == 0 (No Cloud shadow)  
- Adjacent to cloud/shadow == 0 (No Adjacent to cloud/shadow)
- Snow/ice == 0 (No Snow/ice)
- Water == 0 (No Water)
- aerosol leve == "Climatology aerosol" (No Low, Moderate, and High aerosol level)

meaning that any pixel that does not meet the criteria outlined above will be removed and set to `_FillValue` in the output files.  

The quality table for the HLS `Fmask` can be found in section 6.4 of the [HLS V2.0 User Guide](https://lpdaac.usgs.gov/documents/1118/HLS_User_Guide_V2.pdf).  

If you do not want the data to be quality filtered, set argument `qf` to `False`.  

### Output File Formats  

Cloud-Optimized GeoTIFF (COG) is the default output file format. If NetCDF-4 (NC4) or ZARR store (ZARR) are selected by the user as the output file format, the script will export a single NC4/ZARR file for each HLS tile returned by the query, in the source HLS projection. Zarr is a file format that stores data in chunked, compressed N-dimensional arrays. Read more about Zarr at: https://zarr.readthedocs.io/.  

#### Output File Names  

The standard format  for HLS S30 V2.0 and HLS L30 V2.0 filenames is as follows:  
**ex:** HLS.S30.T17SLU.2020117T160901.v2.0.B8A.tif  
> **HLS.S30/HLS.L30**: Product Short Name  
  **T17SLU**: MGRS Tile ID (T+5-digits)  
  **2020117T160901**: Julian Date and Time of Acquisition (YYYYDDDTHHMMSS)  
  **v2.0**: Product Version  
  **B8A/B05**: Spectral Band  
  **.tif**: Data Format (Cloud Optimized GeoTIFF)  

For additional information on HLS naming conventions, be sure to check out the [HLS Overview Page](https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/#hls-naming-conventions).  

If you selected COG as the output file format, the output file name will simply include **.subset.tif** at the end of the filename:  
> HLS.S30.T17SLU.2020117T160901.v2.0.B8A.subset.tif  

If you selected nc4 or Zarr as the output file format, the following naming convention will be used:  
**ex:** HLS.T17SLU.10_24_2020.11_10_2020.subset.nc4  
> HLS.[MGRS Tile ID].[date of first observation in output file].[date of last observation in output file].subset.zarr/nc4  

---

## Contact Information  

**Email:** LPDAAC@usgs.gov  
**Voice:** +1-866-573-3222  
**Organization:** Land Processes Distributed Active Archive Center (LP DAAC)  
**Website:** [https://lpdaac.usgs.gov/](https://lpdaac.usgs.gov/)  
**Date last modified:** 07-28-2023  

¹KBR, Inc., contractor to the U.S. Geological Survey, Earth Resources Observation and Science (EROS) Center,  
 Sioux Falls, South Dakota, USA. Work performed under USGS contract G15PD00467 for LP DAAC².  
²LP DAAC Work performed under NASA contract NNG14HH33I.
