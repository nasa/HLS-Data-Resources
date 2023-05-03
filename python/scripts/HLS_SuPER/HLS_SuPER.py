# -*- coding: utf-8 -*-
"""
===============================================================================
HLS Subsetting, Processing, and Exporting Reformatted Data Prep Script                                  
Authors: Cole Krehbiel and Mahsa Jami                                                   
Last Updated: 07-18-2022  
Last Updated by Mahsa Jami                                             
===============================================================================
"""
######################### IMPORT PACKAGES #####################################
import argparse
import sys
from shapely.geometry import box
import geopandas as gp
import os
import datetime as dt

######################### USER-DEFINED VARIABLES ##############################
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description='Performs Spatial/Temporal/Band Subsetting, Processing, and Customized Exporting for HLS V2.0 files')

# roi: Region of interest as shapefile, geojson, or comma separated LL Lon, LL Lat, UR Lon, UR Lat 
parser.add_argument('-roi', type=str, nargs='*', required=True, help="(Required) Region of Interest (ROI) for spatial subset. \
                    Valid inputs are: (1) a geojson or shapefile (absolute path to file required if not in same directory as this script), or \
                    (2) bounding box coordinates: 'LowerLeft_lon,LowerLeft_lat,UpperRight_lon,UpperRight_lat'\
                    NOTE: Negative coordinates MUST be written in single quotation marks '-120,43,-118,48'\
                    NOTE 2: If providing an absolute path with spaces in directory names, please use double quotation marks "" ")

# dir: Directory to save the files to
parser.add_argument('-dir', required=False, help='Directory to export output HLS files to.', default=os.getcwd())

# start: Start Date
parser.add_argument('-start', required=False, help='Start date for time period of interest: valid format is mm/dd/yyyy (e.g. 10/20/2020).', default='04/03/2014')

# end: End Date
parser.add_argument('-end', required=False, help='Start date for time period of interest: valid format is mm/dd/yyyy (e.g. 10/24/2020).', default=dt.datetime.today().strftime ("%m/%d/%Y"))                    

# prod: product(s) desired to be downloaded
parser.add_argument('-prod' ,choices = ['HLSS30' , 'HLSL30', 'both'] ,required=False, help='Desired product(s) to be subset and processed.', default='both')

# layers: layers desired to be processed within the products selected
parser.add_argument('-bands', required=False, help="Desired layers to be processed. Valid inputs are ALL, COASTAL-AEROSOL, BLUE, GREEN, RED, RED-EDGE1, RED-EDGE2, RED-EDGE3, NIR1, SWIR1, SWIR2, CIRRUS, TIR1, TIR2, WATER-VAPOR, FMASK, VZA, VAA, SZA, SAA. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names.", default='ALL')

# cc: maximum cloud cover (%) allowed to be returned (by scene) 
parser.add_argument('-cc', required=False, help='Maximum (scene-level) cloud cover (percent) allowed for returned observations (e.g. 35). Valid range: 0 to 100 (integers only)', default='100')                    

# qf: quality filter flag: filter out poor quality data yes/no
parser.add_argument('-qf' ,choices = ['True', 'False'], required=False, help='Flag to quality filter before exporting output files (see README for quality filtering performed).', default='True')

# sf: scale factor flag: Scale data or leave unscaled yes/no
parser.add_argument('-scale' ,choices = ['True', 'False'], required=False, help='Flag to apply scale factor to layers before exporting output files.', default='True')

# of: output file format
parser.add_argument('-of' ,choices = ['COG', 'NC4', 'ZARR'], required=False, help='Define the desired output file format', default='COG')

args = parser.parse_args()

######################### Handle Inputs #######################################
# REGION OF INTEREST ----------------------------------------------------------
ROI = args.roi

# Verify ROI is valid
if type(ROI) == list:
    # if submitted as a list, reformat to a comma separated string
    ROI_s = ''
    for c in ROI: ROI_s += f'{c},'
    ROI = ROI_s[:-1]
    
if ROI.endswith(('json', 'shp')): 
    # Read file in and grab bounds
    try:
        bbox = gp.GeoDataFrame.from_file(ROI)
        
        # Check if ROI is in Geographic CRS, if not, convert to it
        if bbox.crs.is_geographic:
            bbox.crs = 'EPSG:4326'
        else:
            bbox.to_crs("EPSG:4326", inplace=True)
            print("Note: ROI submitted is being converted to Geographic CRS (EPSG:4326)")
        # Check for number of features included in ROI
        if len(bbox) > 1:                                                            
            print('Multi-feature polygon detected. Only the first feature will be used.')
            bbox = bbox[0:1]
    except:
        sys.exit(f"The GeoJSON/shapefile is either not valid or could not be found.\nPlease double check the name and provide the absolute path to the file or make sure that it is located in {os.getcwd()}")     
    
    # Verify the geometry is valid and convert to comma separated string
    if  bbox['geometry'][0].is_valid:
        bounding_box = [b for b in bbox['geometry'][0].bounds]
        bbox_string = ''
        for b in bounding_box: bbox_string += f"{b},"
        bbox_string = bbox_string[:-1]
    else:
        sys.exit(f"The GeoJSON/shapefile: {ROI} is not valid.")
        
# Verify bounding box coords
else:
    if len(ROI.split(',')) != 4:
        sys.exit("Valid roi options include: geojson (.json or .geojson), shapefile (.shp), or a comma separated string containing bounding box coordinates: 'LL-Lon,LL-Lat,UR-Lon,UR-Lat' (single quotes included)")
    else:
        try:
            bbox = [float(rr.strip(']').strip('[').strip("'").strip('"').strip(' ')) for rr in ROI.split(',')]
        except ValueError:
            sys.exit('Invalid coordinate detected in roi provided. Valid bbox coordinates must be numbers (int or float).')
        
        # Check that bbox coords are within the bounds of geographic CRS
        if bbox[0] < -180 or bbox[0] > 180:
            sys.exit(f"{bbox[0]} is not a valid entry for LL-lon (valid range is -180 to 180)")
        if bbox[2] < -180 or bbox[2] > 180:
            sys.exit(f"{bbox[2]} is not a valid entry for UR-lon (valid range is -180 to 180)")
        if bbox[1] < -90 or bbox[1] > 90:
            sys.exit(f"{bbox[1]} is not a valid entry for LL-lat (valid range is -90 to 90)")
        if bbox[3] < -90 or bbox[3] > 90:
            sys.exit(f"{bbox[3]} is not a valid entry for UR-lat (valid range is -90 to 90)")
        
        # Shapely automatically flips coords based on min/max x, y
        bbox_shape = box(bbox[0],bbox[1],bbox[2],bbox[3]) 
        if  bbox_shape.is_valid:
            bounding_box = [b for b in bbox_shape.bounds]
            bbox_string = ''
            for b in bounding_box: bbox_string += f"{b},"
            bbox_string = bbox_string[:-1]
        else:
            sys.exit(f"The GeoJSON/shapefile: {ROI} is not valid.")     

# OUTPUT DIRECTORY ------------------------------------------------------------
# Set working directory from user-defined arg
if args.dir is not None:
    outDir = os.path.normpath(args.dir.strip("'").strip('"')) + os.sep  
else: 
    outDir = os.getcwd() + os.sep     # Defaults to the current directory 

# Verify that the directory either exists or can be created and accessed
try:
    if not os.path.exists(outDir): os.makedirs(outDir)
    os.chdir(outDir)
except:
    sys.exit(f'{args.dir} is not a valid directory.')

# DATES -----------------------------------------------------------------------
start_date = args.start.strip("'").strip('"')  # Assign start date to variable 
end_date = args.end.strip("'").strip('"')      # Assign end date to variable

# Validate the format of the dates submitted
def date_validate(date):
    try:
        dated = dt.datetime.strptime(date, '%m/%d/%Y')
    except:
        sys.exit(f"The date: {date} is not valid. The valid format is mm/dd/yyyy (e.g. 10/20/2020)")
    return dated

start, end = date_validate(start_date),  date_validate(end_date)

# Verify that start date is either the same day or before end date
if start > end:
    sys.exit(f"The Start Date requested: {start} is after the End Date Requested: {end}.")
else:      
    # Change the date format to match CMR-STAC requirements
    dates = f'{start.strftime("%Y")}-{start.strftime("%m")}-{start.strftime("%d")}T00:00:00Z/{end.strftime("%Y")}-{end.strftime("%m")}-{end.strftime("%d")}T23:59:59Z'                  

# PRODUCTS --------------------------------------------------------------------
prod = args.prod

# Create dictionary of shortnames for HLS products
shortname = {'HLSS30': 'HLSS30.v2.0', 'HLSL30': 'HLSL30.v2.0'}   

# Create a dictionary with product name and shortname
if prod == 'both':
    prods = shortname
else:
    prods = {prod: shortname[prod]}

# BANDS/LAYERS ----------------------------------------------------------------
# Strip spacing, quotes, make all upper case and create a list
bands = args.bands.strip(' ').strip("'").strip('"').upper() 
band_list = bands.split(',')

# Create a LUT dict including the HLS product bands mapped to names
lut = {'HLSS30': {'COASTAL-AEROSOL':'B01', 'BLUE':'B02', 'GREEN':'B03', 'RED':'B04', 'RED-EDGE1':'B05', 'RED-EDGE2':'B06', 'RED-EDGE3':'B07', 'NIR-Broad':'B08', 'NIR1':'B8A', 'WATER-VAPOR':'B09', 'CIRRUS':'B10', 'SWIR1':'B11', 'SWIR2':'B12', 'FMASK':'Fmask', 'VZA': 'VZA', 'VAA': 'VAA', 'SZA': 'SZA', 'SAA': 'SAA'},
       'HLSL30': {'COASTAL-AEROSOL':'B01', 'BLUE':'B02', 'GREEN':'B03', 'RED':'B04', 'NIR1':'B05', 'SWIR1':'B06','SWIR2':'B07', 'CIRRUS':'B09', 'TIR1':'B10', 'TIR2':'B11', 'FMASK':'Fmask', 'VZA': 'VZA', 'VAA': 'VAA', 'SZA': 'SZA', 'SAA': 'SAA'}}

# List of all available/acceptable band names
all_bands = ['ALL', 'COASTAL-AEROSOL', 'BLUE', 'GREEN', 'RED', 'RED-EDGE1', 'RED-EDGE2', 'RED-EDGE3', 'NIR1', 'SWIR1', 'SWIR2', 'CIRRUS', 'TIR1', 'TIR2', 'WATER-VAPOR', 'FMASK', 'VZA', 'VAA', 'SZA', 'SAA']

# Validate that bands are named correctly
for b in band_list:
    if b not in all_bands:
        sys.exit(f"Band: {b} is not a valid input option. Valid inputs are ALL, COASTAL-AEROSOL, BLUE, GREEN, RED, RED-EDGE1, RED-EDGE2, RED-EDGE3, NIR1, SWIR1, SWIR2, CIRRUS, TIR1, TIR2, WATER-VAPOR, FMASK, VZA, VAA, SZA, SAA. To request multiple layers, provide them in comma separated format with no spaces. Unsure of the names for your bands?--check out the README which contains a table of all bands and band names.")

# Set up a dictionary of band names and numbers by product
band_dict = {}
for p in prods:
    band_dict[p] = {}
    for b in band_list:
        if b == 'ALL':
            band_dict[p] = lut[p]
        else:
            try:
                band_dict[p][b] = lut[p][b]
            except:
                print(f"Product {p} does not contain band {b}")

# CLOUD COVER -----------------------------------------------------------------
# Make sure cc is a valid integer
try:
    cc = int(args.cc.strip("'").strip('"'))
except: 
    sys.exit(f"{args.cc} is not a valid input for filtering by cloud cover (e.g. 35). Valid range: 0 to 100 (integers only)")
    
# Validate that cc is in the valid range (0-100)
if cc < 0 or cc > 100:
    sys.exit(f"{args.cc} is not a valid input option for filtering by cloud cover (e.g. 35). Valid range: 0 to 100 (integers only)")

# QUALITY FILTERING -----------------------------------------------------------
qf = args.qf

# Convert string to boolean (True is default)
if qf == 'True': qf = True
else: qf = False

# SCALE FACTOR ----------------------------------------------------------------
scale = args.scale

# Convert string to boolean (True is default)
if scale == 'True': scale = True
else: scale = False  

#  OUTPUT FORMAT --------------------------------------------------------------
of = args.of

# FILE LIST -------------------------------------------------------------------
fileList = f"{outDir}HLS_SuPER_links.txt"

########################### SEARCH AND SUBSET #################################
os.chdir(sys.path[0])  # Switch back to the script directory to execute

# Call HLS_Su.py using inputs provided
from HLS_Su import hls_subset

# Query CMR-STAC
dl = hls_subset(bbox_string, outDir, dates, prods, band_dict, cc)  

#################### PROCESS AND EXPORT REFORMATTED ###########################
# If user decides to continue downloading the intersecting files:
if dl[0].lower() == 'y': 
    os.chdir(sys.path[0])  # Switch back to the script directory to execute
    
    # Call HLS_PER.py using inputs provided and output text file from HLS_Su.py
    from HLS_PER import hls_process
    hls_process(outDir, ROI, qf, scale, of, fileList)  # Access Data, Scale/QF, Export

#################### PROCESS AND EXPORT REFORMATTED (2) #######################
# If any of the downloads failed, retry processing one more time
fileList = f"{outDir}HLS_SuPER_links_failed.txt"

if os.path.exists(fileList):
    os.chdir(sys.path[0])  # Switch back to the script directory to execute
    
    # Call HLS_PER.py using inputs provided and output text file from HLS_Su.py
    from HLS_PER import hls_process
    hls_process(outDir, ROI, qf, scale, of, fileList)  # Access Data, Scale/QF, Export

###############################################################################
# Delete the failed downloads if exist (the ones that ended up DLing successfully)