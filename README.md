# HLS-Data-Resources  

Welcome! This repository provides guides, short how-tos, and tutorials to help users access and work with Harmonized Landsat Sentinel-2 (HLS) data. In the interest of open science this repository has been made public but is still under active development. All Jupyter notebooks and scripts should be functional, however, changes or additions may be made. Contributions from all parties are welcome.  

## Resources  

Below are data use resources available HLS data.  

|Name|Type/Link|Summary|Services and Tools|
|----|---------|-------|------------------|
| HLS Python Tutorial | [Python Notebook](python/tutorials/HLS_Tutorial.ipynb) | Tutorial demonstrating how to search for, access, and process HLS data in Python | [earthaccess](https://github.com/nsidc/earthaccess) |
|EVI Timeseries with ODC-STAC | [Python Notebook](python/tutorials/EVI_timeseries_with_odc_stac.ipynb) | Tutorial demonstrating how to use the Open Data Cube (ODC) and CMR-STAC to create an EVI time series very efficiently | [CMR STAC API](https://cmr.earthdata.nasa.gov/stac) |
| HLS SuPER Script | [Python Script](python/scripts/HLS_SuPER/) | Find, download, and subset HLS data from a command line executable | [CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) |
| HLS Bulk Download Bash Script | [Bash Script](bash/hls-bulk-download/)| Find and download | [CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) |
|HLS R Tutorial | [R Markdown](r/HLS_Tutorial.Rmd) | Tutorial demonstrating how to search for, access, and process HLS data in R | [CMR STAC API](https://cmr.earthdata.nasa.gov/stac) |

**Additionally, the [LPDAAC-Data-Resources](https://github.com/nasa/LPDAAC-Data-Resources) Repository has general resources associated with datasets hosted by the LP DAAC, as well as links to other repositories for specific datasets such as EMIT, ECOSTRESS, and GEDI.**

## HLS Background

The  Harmonized Landsat Sentinel-2 ([HLS](https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/)) project produces seamless, harmonized surface reflectance data from the Operational Land Imager (OLI) and Multi-Spectral Instrument (MSI) aboard Landsat and Sentinel-2 Earth-observing satellites, respectively. The aim is to produce seamless products with normalized parameters, which include atmospheric correction, cloud and cloud-shadow masking, geographic co-registration and common gridding, normalized bidirectional reflectance distribution function, and spectral band adjustment. This will provide global observation of the Earth’s surface every 2-3 days with 30 meter spatial resolution. One of the major applications that will benefit from HLS is agriculture assessment and monitoring, which is used as the use case for this tutorial.

## Prerequisites/Setup Instructions

Instructions for setting up a compatible environment for accessing HLS data are linked to below.

- [Python set up instructions](https://github.com/nasa/LPDAAC-Data-Resources/blob/main/setup/setup_instructions_python.md)

## Helpful Links  

- [LP DAAC Data Resources GitHub](https://github.com/nasa/LPDAAC-Data-Resources)
- [HLSL30 V2 Product Page](https://www.doi.org/10.5067/HLS/HLSL30.002)  
- [HLSS30 V2 Product Page](https://www.doi.org/10.5067/HLS/HLSS30.002)  
- [HLS on Earthdata Search](https://search.earthdata.nasa.gov/search?q=%22HLSS30%22)  
- [HLS V2 User Guide](https://lpdaac.usgs.gov/documents/1326/HLS_User_Guide_V2.pdf)  
- [HLS Data Resources Repository](https://github.com/nasa/HLS-Data-Resources)  

## Contact Info  

Email: <LPDAAC@usgs.gov>  
Voice: +1-866-573-3222  
Organization: Land Processes Distributed Active Archive Center (LP DAAC)¹  
Website: <https://lpdaac.usgs.gov/>  
Date last modified: 01-19-2023  

¹Work performed under USGS contract G15PD00467 for NASA contract NNG14HH33I.  
