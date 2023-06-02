# HLS-Data-Resources  

Welcome! This repository provides guides, short how-tos, and tutorials to help users access and work with Harmonized Landsat Sentinel-2 (HLS) data. In the interest of open science this repository has been made public but is still under active development. All Jupyter notebooks and scripts should be functional, however, changes or additions may be made. Contributions from all parties are welcome.  

## Resources  

Below are data use resources available HLS data.  

|Name|Type/Link|Summary|Services and Tools|
|----|---------|-------|------------------|
| HLS_Tutorial | [Python Notebook](python/tutorials/HLS_Tutorial.ipynb) | Tutorial demonstrating how to search for, access, and process HLS data | CMR-STAC API |
| HLS SuPER Script | [Python Script](python/scripts/HLS_SuPER/) | Find, download, and subset HLS data from a command line executable | CMR-STAC API |

## HLS Background

The  Harmonized Landsat Sentinel-2 ([HLS](https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/)) project produces seamless, harmonized surface reflectance data from the Operational Land Imager (OLI) and Multi-Spectral Instrument (MSI) aboard Landsat and Sentinel-2 Earth-observing satellites, respectively. The aim is to produce seamless products with normalized parameters, which include atmospheric correction, cloud and cloud-shadow masking, geographic co-registration and common gridding, normalized bidirectional reflectance distribution function, and spectral band adjustment. This will provide global observation of the Earth’s surface every 2-3 days with 30 meter spatial resolution. One of the major applications that will benefit from HLS is agriculture assessment and monitoring, which is used as the use case for this tutorial.

## Prerequisites/Setup Instructions

This repository requires that users set up a compatible Python environment and download the EMIT granules used. See the `setup_instuctions.md` file in the `./setup/` folder.

## Helpful Links  

- HLS Product Pages:  
- [HLS on Earth Data Search]()  
- HLS User Guides:
- [HLS Data Resources Repository]()  

## Contact Info  

Email: LPDAAC@usgs.gov  
Voice: +1-866-573-3222  
Organization: Land Processes Distributed Active Archive Center (LP DAAC)¹  
Website: <https://lpdaac.usgs.gov/>  
Date last modified: 05-15-2023  

¹Work performed under USGS contract G15PD00467 for NASA contract NNG14HH33I.  
