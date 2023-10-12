# Download HLS data from LP DAAC Cloud Archive

The [Harmonized Landsat Sentinel-2 (HLS)](https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/harmonized-landsat-sentinel-2-hls-overview/) version 2.0 (v2) collection is archived and distributed by NASA's [Land Processes Distributed Active Archive Center](https://lpdaac.usgs.gov/) (LP DAAC). HLS v2 provide consistent science quality surface reflectance (SR) and top of atmosphere (TOA) brightness data from the Operational Land Imager (OLI) aboard the joint NASA/USGS Landsat 8 satellite ([HLSL30](https://doi.org/10.5067/HLS/HLSL30.002)) and the Multi-Spectral Instrument (MSI) aboard the European Space Agency (ESA) Sentinel-2A and Sentinel-2B satellites ([HLSS30](https://doi.org/10.5067/HLS/HLSS30.002)). The combined measurement enables global observations of the land every 2–3 days at 30 meter (m) spatial resolution. These data are available from [LP DAAC Cumulus cloud archive](https://search.earthdata.nasa.gov/search?q=HLS%20v2.0) as [Cloud Optimized GeoTIFFs](https://www.cogeo.org/) (COG).  

The `getHLS.sh` script was created to not only bulk download HLS data for a given HLS tile ID and date range (along with other filtering parameters), but also identify and download previously unavailable granules without redownloading previously found granules.

## Requirements

</br>

> **DISCLAIMER**  
>
> - A [Bash shell](https://git-scm.com/download/win) is required for the execution of the `getHLS.sh` script.
> - The `getHLS.sh` script has been tested on Mac OS, Ubuntu 20.04, and Windows OS.  
> - **!!!** On Windows OS, [Git Bash](https://git-scm.com/download/win) was the only shell to successfully execute the `getHLS.sh` script. Testing of the script in other common environments with Linux shells (e.g., [Cygwin](https://www.cygwin.com/)) is on-going.

</br>

### 1. NASA Earthdata Login Account

To download HLS data from any client, users must have a NASA Earthdata Login account. Please visit <https://urs.earthdata.nasa.gov> to register and manage your Earthdata Login account. This account is free to create and only takes a moment to set up.

### 2. netrc File

A netrc file containing your NASA Earthdata Login credentials is needed for the script to authenticate and download HLS data. The file must be placed in the user's `HOME` (Mac or Linux OS) or `USERPROFILE` (Window OS) directory and must be saved as `.netrc` containing the information below:  

```text
machine urs.earthdata.nasa.gov login <EDL Username> password <EDL Password>
```

where `<EDL Username>` is the user's Earthdata Login username and `<EDL Passwor>` is the user's Earthdata Login password.

### 3. Get `getHLS.sh` Script

[Download](https://git.earthdata.nasa.gov/rest/api/latest/projects/LPDUR/repos/hls-bulk-download/archive?format=zip) or clone the [HLS-Bulk-Download](https://git.earthdata.nasa.gov/projects/LPDUR/repos/hls-bulk-download/browse) to a local directory.

### 4. Bash shell and File Permissions

The `getHLS.sh` script mush be [run from a Bash shell](https://devconnected.com/how-to-run-a-bash-script/). Additionally, the [file permissions](https://www.linux.com/training-tutorials/understanding-linux-file-permissions/) must be set to allow the user to execute the script. The permissions can be set using the Bash shell. From the shell, navigate to the directory containing the `getHLS.sh`.  

#### EXAMPLE

```text
λ cd ./hls-bulk-download

λ ls
getHLS.sh  README.md  tmp.tileid.txt
```

Next, change the permissions so that the user can execute the script. This can be achieved by running the command below.

```text
λ chmod u+rwx getHLS.sh
```

The user may already have permissions to execute. In this case, explicitly setting the permissions will not have a negative impact.

## Features

1. Query the NASA Common Metadata Repository (CMR) based on HLS tile ID, date range, cloud cover, spatial cover, etc., to get a list of HLS files for downloading  
2. Organize the HLS files into subdirectories based on data type (L30/S30), year, tile ID, and granule name  
3. Uses [wget](https://www.gnu.org/software/wget/) or [curl](https://curl.se/), depending on which is available on the user's system, to run multiple download processes in parallel (see [Additional Configuration Options](#additional-configuration-options))  
4. A second invocation will not download files that have been downloaded before. Only files that were missing and/or modified since the last invocation will be downloaded.  

## Script parameters

The required positional parameters for commandline execution of the `getHLS.sh` script are below. For additional configuration options (i.e., cloud cover and spatial coverage), see the [Additional Configuration Options](#additional-configuration-options) section of this document.  

```text
<tilelist> <date_begin> <date_end> <out_dir>
```

where:  

- `<tilelist>` is a text file containing the 5-character tile IDs. **NOTE**, each entry **must** be separated by a space (see [tmp.tileid.txt](./tmp.tileid.txt)). **DO NOT** add a new line after a tile ID entry.  

    **EXAMPLE**

    ```text
    λ cat tileid_file.txt
    37QGC 10SGJ
    ```

- `<date_begin>` is the start of the sensing date (yyyy-mm-dd)  

    **EXAMPLE**

    ```text
    2021-07-01
    ```

- `<date_end>` is the end of the sensing date - inclusive (yyyy-mm-dd)  

    **EXAMPLE**

    ```text
    2021-07-30
    ```

- `<out_dir>` is the base directory of output<sup>1</sup>

    **EXAMPLE**

    ```text
    outdir
    ```

<sup>1</sup> The base directory does not have to exist prior to the execution of the script. The directory will be created with subdirectories that bin the data being downloaded.  

## Script Executions

To execute the script, the call must take the form below:

```text
λ ./getHLS.sh <tilelist> <date_begin> <date_end> <out_dir>
```

Using the example parameters described above, a fully parameterized call looks like:

```text
λ ./getHLS.sh tileid_file.txt 2021-07-01 2021-07-30 outdir
```

## Additional Configuration Options

The script has three additional parameters that can be modified to either refine the search query further or increase the number of download processes to run. These additional parameter are only configurable **within** the `getHLS.sh` script itself. The parameters are:  

- `NP` (line 59) specifies how many download processes to run. The default is 10; can be modified based on the capacity of the local computer.  
- `CLOUD` (line 60) is the maximum amount of cloud cover in %  
- `SPATIAL` (line 61) is the minimum amount of spatial coverage within the tile in %  

> **NOTE**  
> To modify the values for `NP`, `CLOUD`, and/or `SPATIAL`, open `getHLS.sh` in a text editor and change the value on the **right** side of the equal (=) sign.

---

## Contact Information

**Author:** Dr. Junchang Ju (Made available by NASA's LP DAAC)  
**Contact:** LPDAAC@usgs.gov  
**Date Last Modified:** See [CHANGELOG.md](./CHANGELOG.md)  
