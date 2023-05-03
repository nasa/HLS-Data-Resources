# -*- coding: utf-8 -*-
"""
===============================================================================
HLS Export Reformatted Data Prep Script
The following Python code will read in a text file of links to HLS data,
access subsets of those data using the defined ROI, [optionally] perform basic
quality filtering, apply the scale factor, and export in the user-defined
output file format.
-------------------------------------------------------------------------------
Authors: Cole Krehbiel and Mahsa Jami
Last Updated: 01-29-2021
===============================================================================
"""

# Define the script as a function and use the inputs provided by HLS_SuPER.py:
def hls_process(outDir, ROI, qf, scale, of, fileList):
    ######################### IMPORT PACKAGES #################################
    import os
    import rasterio as rio
    from osgeo import gdal
    import pyproj
    from shapely.ops import transform
    from shapely.geometry import box
    from rasterio.mask import mask
    from rasterio.shutil import copy
    import numpy as np
    from rasterio.enums import Resampling
    import requests as r
    import geopandas as gp
    from netrc import netrc
    from subprocess import Popen
    from subprocess import DEVNULL, STDOUT
    from getpass import getpass
    from pyproj import CRS
    from datetime import datetime
    import warnings
    from sys import platform

    ######################### HANDLE INPUTS ###################################
    os.chdir(outDir)
    out_file = fileList  # text file of HLS links from HLS_Su.py
    failed = []          # Store any files that fail to be downloaded
    
    # Read in links file
    with open(out_file) as f: files = f.read().splitlines()
    f.close()

    # Convert file list to dictionary
    file_dict = {}
    ancillary_files = []
    for f in files:
        # Create a list of ancillary files to be downloaded
        if f.endswith('.jpg') or f.endswith('.xml'):
            ancillary_files.append(f)
        else:
            # Use tilename + observation time to group into dictionary keys
            tile_time = f"{f.split('.')[-6]}.{f.split('.')[-5]}"
            if tile_time not in file_dict.keys():
                file_dict[tile_time] = [f]
            else:
                file_dict[tile_time].append(f)

    # Convert bbox, shapefile, or geojson (from input args) to shapely polygon
    if ROI.endswith('.shp') or ROI.endswith('json'):
        if len(gp.read_file(ROI)['geometry']) > 1:
            print('Multi-feature polygon detected. This script will only process the first feature.')
        bbox = gp.read_file(ROI)

        # Check if ROI is in Geographic CRS, if not, convert to it
        if bbox.crs.is_geographic:
            bbox.crs = 'EPSG:4326'
        else:
            bbox.to_crs("EPSG:4326", inplace=True)
        roi_shape = bbox['geometry'][0]

    else:
        bbox = [float(rr.strip(']').strip('[').strip("'").strip('"').strip(' ')) for rr in ROI.split(',')]
        roi_shape = box(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

    ######################## AUTHENTICATION ###################################
    # GDAL configs used to successfully access LP DAAC Cloud Assets via vsicurl
    gdal.SetConfigOption("GDAL_HTTP_UNSAFESSL", "YES")
    gdal.SetConfigOption('GDAL_HTTP_COOKIEFILE','~/cookies.txt')
    gdal.SetConfigOption('GDAL_HTTP_COOKIEJAR', '~/cookies.txt')
    gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN','FALSE')
    gdal.SetConfigOption('CPL_VSIL_CURL_ALLOWED_EXTENSIONS','TIF')

    # Verify a netrc is set up with Earthdata Login Username and password
    urs = 'urs.earthdata.nasa.gov'    # Earthdata URL to call for authentication
    prompts = ['Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ','Enter NASA Earthdata Login Password: ']

    # Determine if netrc file exists, and if it includes NASA Earthdata Login Credentials
    if 'win' in platform:
        nrc = '_netrc'
    else:
        nrc = '.netrc'
    try:
        netrcDir = os.path.expanduser(f"~/{nrc}")
        netrc(netrcDir).authenticators(urs)[0]
        del netrcDir

    # If not, create a netrc file and prompt user for NASA Earthdata Login Username/Password
    except FileNotFoundError:
        homeDir = os.path.expanduser("~")

        # Windows OS won't read the netrc unless this is set
        Popen(f'setx HOME {homeDir}', shell=True, stdout=DEVNULL);

        if nrc == '.netrc':
            Popen(f'touch {homeDir + os.sep}{nrc} | chmod og-rw {homeDir + os.sep}{nrc}', shell=True, stdout=DEVNULL, stderr=STDOUT);

        # Unable to use touch/chmod on Windows OS
        Popen(f'echo machine {urs} >> {homeDir + os.sep}{nrc}', shell=True)
        Popen(f'echo login {getpass(prompt=prompts[0])} >> {homeDir + os.sep}{nrc}', shell=True)
        Popen(f'echo password {getpass(prompt=prompts[1])} >> {homeDir + os.sep}{nrc}', shell=True)
        del homeDir

    # Determine OS and edit netrc file if it exists but is not set up for NASA Earthdata Login
    except TypeError:
        homeDir = os.path.expanduser("~")
        Popen(f'echo machine {urs} >> {homeDir + os.sep}{nrc}', shell=True)
        Popen(f'echo login {getpass(prompt=prompts[0])} >> {homeDir + os.sep}{nrc}', shell=True)
        Popen(f'echo password {getpass(prompt=prompts[1])} >> {homeDir + os.sep}{nrc}', shell=True)
        del homeDir
    del urs, prompts

    ######################## PROCESS FILES ####################################
    # Define source CRS of the ROI
    geo_CRS = pyproj.Proj('+proj=longlat +datum=WGS84 +no_defs', preserve_units=True)
    all_cogs = []
    z = 0

    # Load into memory using ROI and vsicurl (via rasterio)
    for f in file_dict:
        
        # Try to access each item/asset 3 times
        for retry in range(0,3):
            try:
                # Read Quality band
                qa = rio.open([file for file in file_dict[f] if 'Fmask' in file][0])

                # Convert bbox/geojson from EPSG:4326 to local UTM for scene
                utm = pyproj.Proj(qa.crs)                             # Destination CRS read from QA band
                project = pyproj.Transformer.from_proj(geo_CRS, utm)  # Set up src -> dest transformation
                roi_UTM = transform(project.transform, roi_shape)     # Apply reprojection to ROI

                # Subset the fmask quality data (returned by default)
                qa_subset, qa_transform = rio.mask.mask(qa, [roi_UTM], crop=True)

                originalName = qa.name.rsplit('/', 1)[-1] # If only exporting FMASK, use for original name
                
                # Loop through and process all other layers (excluding QA)
                for b in [file for file in file_dict[f] if 'Fmask' not in file]:
                    z += 1

                    # Read file and load in subset
                    band = rio.open(b)
                    subset, btransform = rio.mask.mask(band, [roi_UTM], crop=True)

                    # Filter by quality if desired
                    if qf is True:
                        '''Default Quality filtering here includes: Cloud = No and Cloud Shadow = No'''

                        # List of values meeting quality criteria
                        goodQ = [0,1,4,5,16,17,20,21,32,33,36,37,48,49,52,53,64,
                                 65,68,69,80,81,84,85,96,97,100,101,112,113,116,
                                 117,128,129,132,133,144,145,148,149,160,161,
                                 164,165,176,177,180,181,192,193,196,197,208,
                                 209,212,213,224,225,228,229,240,241,244,245]

                        # Apply QA mask and set masked data to fill value
                        subset = np.ma.MaskedArray(subset, np.in1d(qa_subset, goodQ, invert=True))
                        subset = np.ma.filled(subset, band.meta['nodata'])

                    # Apply scale factor if desired
                    if scale is True:
                        subset = subset[0] * band.scales[0]  # Apply Scale Factor

                        try:
                            # Reset the fill value
                            subset[subset == band.meta['nodata'] * band.scales[0]] = band.meta['nodata']
                        except TypeError:
                            print(f"Fill Value is not provided for band {band.name.rsplit('.', 2)[-2]}")
                    else:
                        subset = subset[0]
                    ################# EXPORT AS COG ###########################
                    # Grab the original HLS S30 granule name
                    originalName = band.name.rsplit('/', 1)[-1]
                    bandName = band.name.rsplit('.', 2)[-2]

                    # Generate output name from the original filename
                    outName = f"{outDir}{originalName.split('.v2.0.')[0]}.v2.0.{bandName}.subset.tif"
                    tempName = f"{outDir}temp.tif"

                    # Create output GeoTIFF with overviews
                    out_tif = rio.open(tempName, 'w', driver='GTiff', height=subset.shape[0], width=subset.shape[1], count=1, dtype=str(subset.dtype), crs=band.crs, transform=btransform)

                    # Write the scaled, quality filtered band to the newly created GeoTIFF
                    out_tif.write(subset, 1)

                    # Define number of overviews from the source data
                    out_tif.build_overviews(band.overviews(1), Resampling.average)  # Calculate overviews
                    out_tif.update_tags(ns='rio_overview', resampling='average')    # Update tags
                    out_tif.nodata = band.meta['nodata']                            # Define fill value
                    kwds = out_tif.profile                                          # Save profile
                    kwds['tiled'] = True
                    kwds['compress'] = 'LZW'
                    out_tif.close()

                    # Open output file, add tiling and compression, and export as valid COG
                    with rio.open(tempName, 'r+') as src:
                        rio.shutil.copy(src, outName, copy_src_overviews=True, **kwds)
                    src.close(), os.remove(tempName)

                    all_cogs.append(outName)  # Update list of outputs
                    print(f"Exported {outName} ({z} of {len(files)})")

                # Export quality layer (Fmask)
                outName = f"{outDir}{originalName.split('.v2.0.')[0]}.v2.0.Fmask.subset.tif"
                tempName = f"{outDir}temp.tif"
                out_tif = rio.open(tempName, 'w', driver='GTiff', height=qa_subset.shape[1], width=qa_subset.shape[2], count=1, dtype=str(qa_subset.dtype), crs=qa.crs, transform=qa_transform)
                out_tif.write(qa_subset[0], 1)
                out_tif.build_overviews(qa.overviews(1), Resampling.average)
                out_tif.update_tags(ns='rio_overview', resampling='average')
                out_tif.nodata = qa.meta['nodata']
                kwds = out_tif.profile
                kwds['tiled'] = True
                kwds['compress'] = 'LZW'
                out_tif.close()
                with rio.open(tempName, 'r+') as src:
                    rio.shutil.copy(src, outName, copy_src_overviews=True, **kwds)
                src.close(), os.remove(tempName)
                all_cogs.append(outName)
                z += 1
                print(f"Exported {outName} ({z} of {len(files)})")
                break
            except:
                print(f"Unable to process assets for item {f}. (Attempt {retry+1} of 3)")
                
                # Add files that are failing to a list
                if retry == 2:
                    for d in file_dict[f]: failed.append(d)
                
    # Download ancillary files
    warnings.filterwarnings('ignore')
    for a in ancillary_files:
        for retry in range(0,3):
            try:
                a_content = r.get(a, verify=False).content
                with open(a.rsplit('/', 1)[-1], 'wb') as handler:
                    handler.write(a_content)
                z += 1
                print(f"Exported {a} ({z} of {len(files)})")
                break
            except:
                print(f"Unable to download {a}. (Attempt {retry+1} of 3)")
                
                # Add files that are failing to a list
                if retry == 2:
                    failed.append(a)

    # If the user asked for COG outputs, end script execution
    if of == 'COG': print(f"All files have been processed and exported to: {outDir}")
    ######################## EXPORT AS NC4 or ZARR ############################
    # Use xarray to stack the cogs into NC4 or ZARR
    else:
        import xarray as xr

        # Split observations by tile (1 nc4/zarr exported per HLS tile)
        tiles = list(np.unique([c.rsplit('.', 7)[1] for c in all_cogs]))
        for t in tiles:
            # If second retry, grab all available files to stack
            if fileList.endswith('failed.txt'):
                cogs = [a for a in os.listdir() if t in a and a.endswith('.tif')]
            else:
                cogs = [a for a in all_cogs if t in a] 

            # Create an output file name using first and last observation date
            times = list(np.unique([datetime.strptime(c.rsplit('.', 7)[2], '%Y%jT%H%M%S') for c in cogs]))
            outName = f"HLS.{t}.{min(times).strftime('%m%d%Y')}.{max(times).strftime('%m%d%Y')}.subset"

            # Create a list of variables so script can create xarray data arrays by variable
            variables = list(np.unique([c.split('.')[-3] for c in cogs]))
            for j,v in enumerate(variables):
                vcogs = [vc for vc in cogs if v in vc]
                for i, c in enumerate(vcogs):

                    # Grab acquisition time from filename
                    time = datetime.strptime(c.rsplit('.v1.5', 1)[0].rsplit('.', 1)[-1], '%Y%jT%H%M%S')

                    # Need to set up the xarray data array for the first file
                    if i == 0:
                        # Open file using rasterio
                        stack = xr.open_rasterio(c)
                        stack = stack.squeeze(drop=True)

                        # Define time coordinate
                        stack.coords['time'] = np.array(time)

                        # Rename coordinates
                        stack = stack.rename({'x':'lon', 'y':'lat', 'time':'time'})
                        stack = stack.expand_dims(dim='time')

                        # Below, set up attributes to be CF-Compliant (1.6)
                        stack.attrs['standard_name'] = v
                        stack.attrs['long_name'] = f"HLS {v}"
                        stack.attrs['missing_value'] = stack.nodatavals[0]
                        stack['x'] = stack.lon
                        stack['y'] = stack.lat
                        stack.x.attrs['axis'] = 'X'
                        stack.x.attrs['standard_name'] = 'projection_x_coordinate'
                        stack.x.attrs['long_name'] = 'x-coordinate in projected coordinate system'
                        stack.y.attrs['axis'] = 'Y'
                        stack.y.attrs['standard_name'] = 'projection_y_coordinate'
                        stack.y.attrs['long_name'] = 'y-coordinate in projected coordinate system'
                        stack.time.attrs['axis'] = 'Z'
                        stack.time['standard_name'] = 'time'
                        stack.time['long_name'] = 'time'
                        stack.lon.attrs['units'] = 'degrees_east'
                        stack.lon.attrs['standard_name'] = 'longitude'
                        stack.lon.attrs['long_name'] = 'longitude'
                        stack.lat.attrs['units'] = 'degrees_north'
                        stack.lat.attrs['standard_name'] = 'latitude'
                        stack.lat.attrs['long_name'] = 'latitude'
                        wkt = CRS.from_epsg(stack.crs.split(':')[-1]).to_wkt()
                        stack['spatial_ref'] = int()
                        stack.spatial_ref.attrs['grid_mapping_name'] = 'transverse_mercator'
                        stack.spatial_ref.attrs['spatial_ref'] = wkt
                        stack.variable.attrs['grid_mapping'] = 'spatial_ref'
                        stack.variable.attrs['_FillValue'] = stack.nodatavals[0]
                        stack.variable.attrs['units'] = 'None'
                        stack.x.attrs['units'] = 'm'
                        stack.y.attrs['units'] = 'm'
                        stack.x.attrs['standard_name'] = 'x'
                        stack.y.attrs['standard_name'] = 'y'
                        stack.spatial_ref.attrs['standard_name'] = 'CRS'
                        stack.time.attrs['standard_name'] = 'time'

                    else:
                        # If data array already set up, add to it
                        S = xr.open_rasterio(c)
                        S = S.squeeze(drop=True)
                        S.coords['time'] = np.array(time)
                        S = S.rename({'x':'lon', 'y':'lat', 'time':'time'})
                        S = S.expand_dims(dim='time')

                        # Concatenate the new array to the data array
                        stack = xr.concat([stack, S], dim='time')
                stack.name = v

                # Now merge data arrays into single dataset
                if j == 0:
                    stack_dataset = stack
                else:
                    stack_dataset = xr.merge([stack_dataset, stack])

            # Make the NetCDF CF-Compliant
            stack_dataset.attrs['Conventions'] = 'CF-1.6'
            stack_dataset.attrs['title'] = 'HLS'
            stack_dataset.attrs['nc.institution'] = 'Unidata'
            stack_dataset.attrs['source'] = 'LP DAAC'
        
            # If this is the second run of HLS_PER.py OR there are no failed files, export
            if len(failed) == 0 or fileList.endswith('failed.txt'):
                
                # Export as NC4 or ZARR
                if of == 'NC4':
                    stack_dataset.to_netcdf(f"{outName}.nc4")
                    print(f"Exported {outName}.nc4")
                else:
                    stack_dataset.to_zarr(f"{outName}.zarr")
                    print(f"Exported {outName}.zarr")
        
        # If this is the second run of HLS_PER.py OR there are no failed files, remove cogs
        if len(failed) == 0 or fileList.endswith('failed.txt'): 
        
            # Remove the COGS
            for a in all_cogs:
                os.remove(a)
    
    # if any files failed, export failed list of links
    if len(failed) != 0:
        out_file2 = f"{outDir}HLS_SuPER_links_failed.txt"
        with open(out_file2, "w") as output:
            for d in failed:
                output.write(f'{d}\n')
                
        # if the files are still failing after second retry, let the user know
        if fileList.endswith('failed.txt'):
            out_file3 = f"{outDir}HLS_SuPER_links_failed_twice.txt"
            with open(out_file3, "w") as output:
                for d in failed:
                    output.write(f'{d}\n')
            print(f"Unable to process  all assets. Check {out_file3} for a list of files that were not processed.")
    
    # Clean up failed file list, so not picked up in future script executions
    if fileList.endswith('failed.txt'):
        os.remove(fileList)