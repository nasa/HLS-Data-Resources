# HLS Subsetting, Processing, and Exporting Reformatted Data Prep Script  

---

## Objective  

NASA's Land Processes Distributed Active Archive Center (LP DAAC) archives and distributes Harmonized Landsat Sentinel-2 (HLS) version 2.0 products in the LP DAAC Cumulus cloud archive as Cloud Optimized GeoTIFFs (COG). the HLS_SuPER.py data prep script is a command line-executable Python script that allows users to submit inputs for their desired spatial (GeoJSON, Shapefile, bounding box) region of interest (ROI), time period of interest, and the specific desired product(s) and bands/layers within the HLS products. The script also includes options for cloud screening observations by a user-defined threshold, quality filtering, applying the scale factor to the data, and users can pick between two output file format options:

  1. COG which returns an output for each source file
  2. NetCDF4 which creates a single output with variables corresponding to bands and stacking all temporal observations for each band.
  
To construct these outputs, the input arguments provided by the user in command line are submitted to NASA's Common Metadata Repository API endpoint via the `earthaccess` Python library to find data. The script then returns a .json containing a nested list of all resulting granules with assets nested within for each HLS observation that intersect the user's input parameters. After outputing this file, it is leveraged to access the cloud-native HLS data for each asset, which are clipped to the ROI provided and exported in the desired output file format. Optionally, data can be quality filtered (see section on quality filtering below) and/or scaled. **This script does not support resampling or reprojection.**

### Available Products  

1. Daily 30 meter (m) global HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance - [HLSS30.002](https://doi.org/10.5067/HLS/HLSS30.002)  

2. Daily 30 meter (m) global HLS Landsat 8 Operational Land Imager Surface Reflectance - [HLSL30.002](https://doi.org/10.5067/HLS/HLSL30.002)  

> **Note:** On November 2021, this data prep script is updated to processes Version 2.0 daily 30 meter (m) global HLS Sentinel-2 Multi-spectral Instrument Surface Reflectance (HLSS30) data and Version 2.0 daily 30 m global HLS Landsat 8 OLI Surface Reflectance (HLSL30) data.  

---

## Prerequisites  

1. **Earthdata Login account**  
    - Create an Earthdata Login account (if you don't already have one) at <https://urs.earthdata.nasa.gov/users/new>
    - Remember your username and password; you will need them to download or access data during the workshop and beyond.
2. **A Local Copy of this Repository**
    - Copy/clone/[download](https://github.com/nasa/HLS-Data-Resources/archive/refs/heads/main.zip) the [HLS-Data-Resources Repository](https://github.com/nasa/HLS-Data-Resources.git). You will need all three of the python scripts downloaded to the same directory on your OS (HLS_Su.py, HLS_PER.py, HLS_SuPER.
3. **Compatible Python Environment**
    - See the [Python Environment Setup](#python-environment-setup) section below.
    - If you have previously set up the [**lpdaac_vitals** environment](https://github.com/nasa/VITALS/blob/main/setup/setup_instructions.md) for a workshop or content from the [VITALS repository](https://github.com/nasa/VITALS/tree/main), you can use that environment for this script as well. 


### Python Environment Setup  

For local Python environment setup we recommend using [mamba](https://mamba.readthedocs.io/en/latest/) to manage Python packages. To install *mamba*, download [miniforge](https://github.com/conda-forge/miniforge) for your operating system.  If using Windows, be sure to check the box to "Add mamba to my PATH environment variable" to enable use of mamba directly from your command line interface. **Note that this may cause an issue if you have an existing mamba install through Anaconda.**  

1. Using your preferred command line interface (command prompt, terminal, cmder, etc.) navigate to your local copy of the repository, then type the following to create a compatible Python environment.

    For Windows:

    ```cmd
    mamba create -n lpdaac_vitals -c conda-forge --yes python=3.10 fiona=1.8.22 gdal hvplot geoviews rioxarray rasterio jupyter geopandas earthaccess jupyter_bokeh h5py h5netcdf spectral scikit-image jupyterlab seaborn dask ray-default
    ```

    For MacOSX:

    ```cmd
    mamba create -n lpdaac_vitals -c conda-forge --yes python=3.10 gdal=3.7.2 hvplot geoviews rioxarray rasterio geopandas fiona=1.9.4 jupyter earthaccess jupyter_bokeh h5py h5netcdf spectral scikit-image seaborn jupyterlab dask ray-default ray-dashboard
    ```

2. Next, activate the Python Environment that you just created.

    ```cmd
    mamba activate lpdaac_vitals 
    ```
**Still having trouble getting a compatible Python environment set up? Contact [LP DAAC User Services](https://lpdaac.usgs.gov/lpdaac-contact-us/).**  

## Script Execution  

1. Once you have completed the prerequisites, open your command line interface navigate to the directory containing the script.
 
2. Ensure your python environment created above is activated.

    ```cmd
    mamba activate lpdaac_vitals 
    ```

3.  The script requires an `roi`, which can be either a shapefile, geojson, or list of bbox coordinates (lower left longitude, lower left latitude, upper right longitude, upper right latitude). Other arguments are optional. See below for some examples of how to execute the script.

```cmd
> python HLS_SuPER.py -roi <insert geojson, shapefile, or bounding box coordinates here> -dir <insert directory to save the output files to>
```  

> **Note:** After running the script, it will show inputs then conduct a search for results. A prompt for a **y/n** will appear to proceed with processing. This is to ensure that the user is away of the quantity of results/files that will be processed.

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
                    [-of {COG,NC4}]  
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
Start date for time period of interest: valid format is yyyy-mm-dd (e.g. 2020-10-20). (default: 2014-04-03)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02  
```  

#### -end END  

```None  
Start date for time period of interest: valid format is mm/dd/yyyy (e.g. 2020-10-20). (default: current date)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24  
```  

#### -prod {HLSS30,HLSL30,both}  

```None  
Desired product(s) to be subset and processed. (default: both)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both  
```  

#### -bands BANDS  

```None  
Desired layers to be processed. Valid inputs are ALL, COASTAL-AEROSOL, BLUE, GREEN, RED, RED-EDGE1, RED-EDGE2, RED-EDGE3, NIR1, SWIR1, SWIR2, CIRRUS, TIR1, TIR2, WATER-VAPOR, FMASK. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names. (default: ALL)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both -bands RED,GREEN,BLUE,NIR1  
```  

#### -cc CC  

```None  
Maximum cloud cover (percent) allowed for returned observations (e.g. 35). Valid range: 0 to 100 (integers only) (default: 100)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50`  
```  

#### -qf {True,False}  

```None  
Flag to quality filter before exporting output files (see section below for quality filtering performed). (default: True)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True  
```  

#### -scale {True,False}  

```None  
Flag to apply scale factor to layers before exporting output files. (default: True)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True -scale False  
```

#### -of {COG,NC4}  

```None  
Define the desired output file format (default: COG)  

Example  
> python HLS_SuPER.py -roi '-120,43,-118,48' -dir C:\Users\HLS\ -start 2020-06-02 -end 2020-10-24 -prod both -bands RED,GREEN,BLUE,NIR1 -cc 50 -qf True -scale False -of NC4  
```  

### Quality Filtering  

If quality filtering is set to True (default), the following quality filtering will be used:  

- Cloud == 0 (No Cloud)  
- Cloud shadow == 0 (No Cloud shadow)  
- Adjacent to cloud/shadow == 0 (No Adjacent to cloud/shadow)
- Snow/ice == 0 (No Snow/ice)
- Water == 0 (No Water)
- aerosol level == Climatology aerosol (No Low, Moderate, and High aerosol level)


meaning that any pixel that does not meet the criteria outlined above will be removed and set to `_FillValue` in the output files.  

The quality table for the HLS `Fmask` can be found in section 6.4 of the [HLS V2.0 User Guide](https://lpdaac.usgs.gov/documents/1118/HLS_User_Guide_V2.pdf).  

If you do not want the data to be quality filtered, set argument `qf` to `False`.  

### Output File Formats  

Cloud-Optimized GeoTIFF (COG) is the default output file format. If NetCDF-4 (NC4) is selected by the user as the output file format, the script will export a single NC4 file for each HLS tile returned by the query, in the source HLS projection. 

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

If you selected COG as the output file format, the output file name will have product specific band names renamed the common names in available bands and include **.subset.tif** at the end of the filename:  
> HLS.S30.T17SLU.2020117T160901.v2.0.NIR1.subset.tif  

If you selected nc4 as the output file format, the following naming convention will be used:  
**ex:** HLS.T17SLU.2020-10-24.2020-11-10.subset.nc4  
> HLS.[MGRS Tile ID].[date of first observation in output file].[date of last observation in output file].subset.nc4  

---

## Contact Info  

Email: <LPDAAC@usgs.gov>  
Voice: +1-866-573-3222  
Organization: Land Processes Distributed Active Archive Center (LP DAAC)¹  
Website: <https://lpdaac.usgs.gov/>  
Date last modified: 2024-09-18  

¹Work performed under USGS contract 140G0121D0001 for NASA contract NNG14HH33I.  
