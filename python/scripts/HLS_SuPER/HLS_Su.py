# -*- coding: utf-8 -*-
"""
===============================================================================
HLS Subsetting Data Prep Script          
The following Python code will search for HLS data by product, layer(s), 
time period, region of interest, and cloud cover. Data will be subset by only 
returning the desired product-layer & spatiotemporal subset defined by the user
-------------------------------------------------------------------------------                        
Authors: Mahsa Jami and Cole Krehbiel                                                   
Last Updated: 03-12-2021                                               
===============================================================================
"""

# Define the script as a function and use the inputs provided by HLS_SuPER.py:
def hls_subset(bbox_string, outDir, dates, prods, band_dict, cc):
    
    # Load necessary packages into Python
    import os
    import requests as r
    import sys

    # ------------------------------SET-UP WORKSPACE------------------------- #
    # Change the working directory
    os.chdir(outDir)
    
    # CMR-STAC API Endpoint for LP DAAC search 
    lp_stac = 'https://cmr.earthdata.nasa.gov/stac/LPCLOUD/search?'   
    
    # ------------------------------PERFORM SEARCH QUERY--------------------- #
    bandLinks = [] # Create an empty list to save the output URLs
    num_tiles = 0

    for b in band_dict:        
        page = 1
        # Attempt to access STAC up to 3 times
        for retry in range(0,3):
            
            # Set up a search query dictionary with all the desired query parameters
            params = {"bbox": bbox_string, "limit": 100, "datetime": dates, "collections": [prods[b]], "page": page}
            #search_query = f"{lp_stac}&collections={prods[b]}&bbox={bbox_string}&datetime={dates}&limit={limit}&page={page}"
            # Post params dict to the CMR-STAC search endpoint
            if r.post(lp_stac, json=params).status_code == 200:        # Check status code for successful query or not
                search_response = r.post(lp_stac, json=params).json()  # Send GET request to retrieve items
                if len(search_response['features']) == 0:     # Raise warning to users that no intersecting files were found
                    print(f'There were no matching outputs found for {b} (Attempt: {retry + 1} of 3)')
                    continue
                else:
                    print(f'There are matching outputs found for {b}')
                    while search_response['numberReturned'] != 0:
                        # Iterate through each item and find the desired assets (layers)
                        for h in search_response['features']:
                            
                            # Filter by cloud cover
                            if h['properties']['eo:cloud_cover'] <= cc:
                                try:
                                    # Always include browse, metadata, and fmask (QA)
                                    bandLinks.append(h['assets']['browse']['href']) 
                                    bandLinks.append(h['assets']['metadata']['href'])
                                    bandLinks.append(h['assets']['Fmask']['href'])
                                    num_tiles += 1
                                except:
                                    print(f"Browse, metadata, and/or Fmask assets were unavailable for {h}")
                                
                                # Now find the desired bands/layers
                                for l in band_dict[b]:
                                    
                                    # Don't duplicate FMASK
                                    if l == 'FMASK': continue
                                
                                    # Skip a single band (asset) if it does not exist for that item
                                    try: 
                                        # Add output links to the list
                                        bandLinks.append(h['assets'][band_dict[b][l]]['href']) 
                                    except:
                                        print(f'{b} band is not available for {h["id"]}') 
                        
                        # Move to the next page until all granules are found
                        page += 1
                        params['page'] = page
                        search_response = r.post(lp_stac, json=params).json()  # Send GET request to retrieve items
                    break
            # Attempt to find the source of an unsuccessful query 
            else:                                                      
                if r.post(lp_stac).status_code != 200: 
                    print(f"ERROR: The CMR-STAC Service is either down or you may not be connected to the internet. (Attempt {retry+1} of 3)")
                elif r.post(lp_stac, json={"bbox": bbox_string, "limit": 100, "collections": [prods[b]]}).status_code != 200:
                    print(f"ERROR: The ROI was rejected by the server. (Attempt {retry+1} of 3)")
                else:
                    print(f"ERROR: The start and/or end dates were rejected by the server. (Attempt {retry+1} of 3)") 

    print(f"\n{num_tiles} granules intersect with your query including {len(bandLinks)} downloadable files.")
    
    # Exit script if no intersecting files found
    if num_tiles == 0:
        sys.exit()
        
    print("Links to those files are saved in the file below:")    
    # Save the links in a text file 
    out_file = f"{outDir}HLS_SuPER_links.txt"
    with open(out_file, "w") as output:
        for link in bandLinks:
            output.write(f'{link}\n')
    print(out_file)
        
    # Ask user if they would like to continue with processing or exit
    dl = input("Would you like to continue downloading these files? (y/n):")
    
    return dl  # Return response to HLS_SuPER.py