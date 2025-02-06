02-06-2025

- Add [EVI_timeseries_with_odc_stac.ipynb](python/tutorials/EVI_timeseries_with_odc_stac.ipynb) to the repository
  - This notebook demonstrates how to use the Open Data Cube (ODC) STAC API to create an EVI time series.

09-17-2024

- Update [HLS_Tutorial.Rmd](r/tutorials/HLS_Tutorial.Rmd)
  - Changed collection identifiers to reflect latest changes to the CMR-STAC API. See [this announcement](https://lpdaac.usgs.gov/news/important-update-to-cmr-stac-new-identifier-and-search-parameter-format/) for more information.  
  - Changed the input bbox formatting. 

08-26-2024

- Update [HLS_Tutorial.Rmd](r/tutorials/HLS_Tutorial.Rmd)
  - Add a new section for Quality Masking
  - Improve readability and vectorize some code chunks

01-19-2024

- Added a retry loop to the [HLS_Tutorial.ipynb](https://github.com/nasa/HLS-Data-Resources/blob/main/python/tutorials/HLS_Tutorial.ipynb) to fix a `vsicurl` error users were getting
- Made minor visual improvements to plots and cell outputs in [HLS_Tutorial.ipynb](https://github.com/nasa/HLS-Data-Resources/blob/main/python/tutorials/HLS_Tutorial.ipynb)
- Updated readme

10-12-2023  

- Added the HLS Bulk Download Bash script to the repository
  - Previous changes include:  

    02-11-2022  

    - getHLS.sh is updated to fix a bug.

    08-30-2021

    - Changed concept ids to query for HLS v2.0
    - Updated readme dates to query granules from the month of July 2021. HLS v2.0 currently does not have granules available for earlier dates.

07-28-2023  

- Updated the authentication with [`earthaccess`](https://github.com/nsidc/earthaccess)

- Updated the quality filtering workflow
- Resolved the error in output creation due to Tiled option
- Added the Scale_factor and add_offset to the unscaled outputs
- Updated the Fmask output creation when data is quality filtered

06-22-2023

- Updated instructions
- Created new .yml file for creating environment
- Updated some plot widths and limits in the tutorial

06-02-2023

- Reworked the HLS tutorial to include:
  - The earthaccess for authentication,
  - The .yml file for environment requirements
  - Made new visualizations
  - Changed the ROI to include the larger area with variation in quality info
-

01-11-2023

- Added The HLS R Tutorial

11-02-2021  

- Geoviews seems to have compatibility issues with Shapely 1.8. Specified Shapely 1.7 in the environment setup instructions.  
- Remove Python env setup instructions from the tutorial. The setup instructions are now only found in the Readme.  

10-25-2021  

- Updated to access HLS v2.0 data  
- Changes to NASA’s Earthdata cloud distribution environment configurations had unintended repercussions with GDAL resulting in the inability to access HLS data via the HTTPS URL. Access issues appear to be resolved by the following PRs:  <https://github.com/OSGeo/gdal/issues/4641> and <https://github.com/OSGeo/gdal/pull/4654>>  
- Updated Python environment requirements to specify GDAL v3.2 - tutorial has been successfully tested using GDAL 3.0, 3.1, and 3.2. Tests with GDAL 3.3 were unsuccessful  
- Updated visualization libraries (e.g., geoviews) to resolve visualization errors in tutorial
- Updated markdown formatting within tutorial
- Updated readme content and format

03-29-2021

- Updated broken links to STAC API spec pages and HLS V1.5 User Guide

03-25-2021

- Added `conda install jupyter notebook --yes` as an instruction to the README and tutorial (issue with `holoviews`/`geoviews` plots not rendering)
- Added a check during automation (section 6) that will skip a file that has already been processed and is available in the current directory  
- Updated the way that the crs is passed to `hvplot()`
- Added `from subprocess import Popen, DEVNULL, STDOUT` to address issue when `_netrc` is not found  
- Added optional `#gdal.SetConfigOption("GDAL_HTTP_UNSAFESSL", "YES")` call for users that need it  
- Updated time series with more observations from March 2021  

03-22-2021

- Removed GDAL config option to turn SSL off (not needed)
- Added `.sortby()` function to the `xarray` data array to assure L30 and S30 observations are ordered chronologically
- Changed the time period of interest to 09-01-2020 to 03-31-2021
- Updated the section on generating a `.netrc` or `_netrc` file based on user platform

03-15-2021

- Updated `collections` to product `shortnames` (in place of `concept_id`) to align with latest release of CMR-STAC.
- Updated logic for search responses with no data found (now returns valid response with `numberReturned` = 0).
- Changed all queries to CMR-STAC LPCLOUD Search endpoint from **GET** requests to **POST** requests.
- Combined `collections` call to LP CLOUD Search endpoint into a single POST request with a list of both HLS products.  
- Updated README with link to CHANGELOG.md  

02-12-2021

- Replaced `bounding_box` with `bbox` and `concept_id` with `collections` to fix breaking change in CMR-STAC search parameter spec and added CHANGELOG.md to repo  

01-26-2021  

- Added Support for HLSL30 V1.5  
- Updated the HLS Script

12-15-2020

- Pull request #5: Added functionality to handle files that are unable to be downloaded
- Fixed COG overviews issue and added filtering for empty observations
- Added functionality to handle files that are unable to be downloaded

11-20-2020

- Pull request #4: Corrected flipped description of bounding box coordinates
- Corrected flipped description of bounding box coordinates

11-19-2020

- Pull request #3: Updated tutorial and readme to reflect cmr-stac updates and peer review suggestions
- Updated tutorial and readme to reflect cmr-stac updates and peer review suggestions

11-17-2020

- Merge pull request #2 in LPDUR/hls-tutorial from develop to master
- Updated code to reflect new STAC endpoint and peer review revisions

10-28-2020

- Merge pull request #1 in LPDUR/hls-tutorial from develop to master
- Updated tutorial and README from AF review
- Updated tutorial and README from AF review

10-27-2020

- updated tutorial and readme from MJ review

10-08-2020

- Added additional guidance on setting up netrc file
- Updated tutorial, README, and added html output and requirements file

09-29-2020

- Initial Commit
