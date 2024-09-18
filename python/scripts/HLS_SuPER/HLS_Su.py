# -*- coding: utf-8 -*-
"""
===============================================================================
This module contains functions related to searching and preprocessing HLS data.

-------------------------------------------------------------------------------                        
Authors: Mahsa Jami, Cole Krehbiel, and Erik Bolch
Contact: lpdaac@usgs.gov                                                   
Last Updated: 2024-09-18                                    
===============================================================================
"""

# Import necessary packages
import numpy as np
import earthaccess


# Main function to search and filter HLS data
def hls_search(bbox: tuple, band_dict: dict, dates=None, cloud_cover=None, log=False):
    """
    This function uses earthaccess to search for HLS data using a bbox and temporal parameter, filter by cloud cover and delivers a list of results urls for the selected bands.
    """
    # Search for data
    results = earthaccess.search_data(
        short_name=list(band_dict.keys()),  # Band dict contains shortnames as keys
        bounding_box=bbox,
        temporal=dates,
    )

    # Filter by cloud cover
    if cloud_cover:
        results = hls_cc_filter(results, cloud_cover)

    # Get results urls
    results_urls = [granule.data_links() for granule in results]

    # Flatten url list
    # results_urls = [item for sublist in results_urls for item in sublist]

    # Filter url list based on selected bands
    selected_results_urls = [
        get_selected_bands_urls(granule_urls, band_dict)
        for granule_urls in results_urls
    ]
    return selected_results_urls


# Filter earthaccess results based on cloud cover threshold
def hls_cc_filter(results, cc_threshold):
    """
    This function filters a list of earthaccess results based on a cloud cover threshold.
    """
    cc = []
    for result in results:
        # Retrieve Cloud Cover from json, convert to float and place in numpy array
        cc.append(
            float(
                next(
                    (
                        aa
                        for aa in result["umm"]["AdditionalAttributes"]
                        if aa.get("Name") == "CLOUD_COVERAGE"
                    ),
                    None,
                )["Values"][0]
            )
        )
    cc = np.array(cc)
    # Find indices based on cloud cover threshold
    cc_indices = np.where(cc <= cc_threshold)
    # Filter results based on indices
    return [results[i] for i in cc_indices[0]]


# Filter results urls based on selected bands
def get_selected_bands_urls(url_list, band_dict):
    """
    This function filters a list of results urls based on HLS collection and selected bands.
    """
    selected_bands_urls = []
    # Loop through urls
    for url in url_list:
        # Filter bands based on band dictionary
        for collection, nested_dict in band_dict.items():
            if collection in url:
                for band in nested_dict.values():
                    if band in url:
                        selected_bands_urls.append(url)
    return selected_bands_urls
