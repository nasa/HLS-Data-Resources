#!/bin/bash

# A bash script to download HLS v2.0 data from LP DAAC. It runs on an OS where
# bash is available: Linux, Mac, (some Windows as well?). An account on
# urs.earthdata.nasa.gov is required.
#
# HLS files are saved in subdirectories of the specified output directory:
#   L30/2025/18/S/U/J/HLS.L30.T18SUJ.2025208T154620.v2.0/
#   S30/2025/18/S/U/J/HLS.S30.T18SUJ.2025219T154819.v2.0
#
# Features include:
#   1) Query CMR metadata by tile ID, date range, cloud cover, and spatial cover
#   2) Paginated CMR queries — no limit on the number of granules returned
#   3) Run multiple download processes in parallel
#   4) Each file is downloaded to a temp path and renamed on success (atomic writes)
#   5) Each file is retried up to 3 times before being marked as failed
#   6) Successfully downloaded files are kept even if other files in the granule fail;
#      failed URLs are written to failed_downloads.txt for re-run
#   7) Re-run mode: pass <failed_downloads.txt> <out_dir> to retry only failed files;
#      already-downloaded files are skipped automatically
#   8) Start/end date order is validated before querying
#
# Command-line parameters:
#   Normal run:  $0 <tilelist> <date_begin> <date_end> <out_dir>
#   Re-run:      $0 <failed_downloads.txt> <out_dir>
#
#   <tilelist>   : text file of 5-character MGRS tile IDs, one per line
#   <date_begin> : start of sensing date range, format YYYY-MM-DD
#   <date_end>   : end of sensing date range, inclusive, format YYYY-MM-DD
#   <out_dir>    : parent output directory; subdirectories are created within it
#
# Implementation notes:
#    1) JSON format is used for CMR metadata queries as it returns file paths directly.
#    2) NP, CLOUD_COVERAGE, and SPATIAL_COVERAGE are adjustable at the top of this script.
#    3) curl on CentOS (NCCS) does not accept the "[]" attribute syntax in CMR queries
#       (exit code 3: globbing error). The "[]"-free syntax is used here for compatibility
#       with both wget and curl across platforms.
#    4) Both wget and curl are supported; curl is preferred when both are available.
#


### Defaults for optional flags
NP=10       # Run this many download processes by default.
CLOUD=100   # Maximum amount of cloud cover in %
SPATIAL=0   # Minimum amount of spatial cover in %

### Parse optional flags first, leaving only positional args
args=()
while [ $# -gt 0 ]
do
    case $1 in
        --cloud)   CLOUD=$2;   shift 2;;
        --spatial) SPATIAL=$2; shift 2;;
        --np)      NP=$2;      shift 2;;
        *)         args+=("$1"); shift;;
    esac
done
set -- "${args[@]}"

if [ $# -eq 2 ]
then
    # Re-run shorthand: <failed_downloads.txt> <out_dir>
    tilelist=$1
    datebeg="N/A"
    dateend="N/A"
    OUTDIR=$2
elif [ $# -eq 4 ]
then
    tilelist=$1
    datebeg=$2
    dateend=$3
    OUTDIR=$4
else
    echo "Usage: $0 <tilelist> <date_begin> <date_end> <out_dir> [--cloud N] [--spatial N] [--np N]" >&2
    echo "where <tilelist> is a text file of 5-character tile IDs" >&2
    echo "      <date_begin> and <date_end> are in the format 2021-12-31" >&2
    echo "      <out_dir> is the parent output directory, within which subdirectories are to be created" >&2
    echo "      --cloud N    maximum cloud cover % (default 100)" >&2
    echo "      --spatial N  minimum spatial cover % (default 0)" >&2
    echo "      --np N       number of parallel download processes (default 10)" >&2
    echo "" >&2
    echo "To retry failed granules: $0 <failed_downloads.txt> <out_dir>" >&2
    exit 1
fi

### Detect re-run mode: 2-arg invocation always means re-run; otherwise check file contents.
RERUN_MODE=false
if [ $# -eq 2 ]; then
    RERUN_MODE=true
elif grep -q '^https://' "$tilelist" 2>/dev/null; then
    RERUN_MODE=true
fi

set -u
set -o pipefail
USER=${USER:-$(id -un 2>/dev/null || echo "user")}    # A setting in case USER is not set in the main script. It is used in the subshells as well.


### export for  subshell. Not needed.  Apr 3, 2026 
#WGETBANDWITH="--limit-rate=2000k  --no-check-certificate"  # "--limit-rate" was suggested by NCCS ADAPT; necessary?
#CURLOPTION="--insecure"        # equivalent to wget's --no-check-certificate

############################### Stop Here! Do Not Enter ##################

### earthdata account
if [ ! -f $HOME/.netrc ]
then
    echo "$HOME/.netrc file unavailable" >&2
    echo "Search the web for how to set up .netrc" >&2
    exit 1
else 
    if ! grep urs.earthdata.nasa.gov $HOME/.netrc -q
    then
        echo "urs.earthdata.nasa.gov entry not found in $HOME/.netrc" >&2
        exit 1
    fi
fi

### Check on date format and order (skip in re-run mode)
if [ $RERUN_MODE = false ]
then
    for d in $datebeg $dateend
    do
        case $d in
          [12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]);;
          *) echo "Given date $d not in the format 2021-12-31" >&2; exit 1;;
            esac
    done
    if [[ "$datebeg" > "$dateend" ]]
    then
        echo "Start date $datebeg is after end date $dateend" >&2
        exit 1
    fi
fi

### Delete the tailing "/" from the output directory name if there is any.
OUTDIR=$(echo $OUTDIR | sed 's:/$::')
FAILREPORT=$OUTDIR/failed_downloads.txt
export OUTDIR FAILREPORT   # Must export for the subshells

### wget/curl availability
WGET=false
CURL=false
which wget >/dev/null 2>&1
if [ $? -eq 0 ]; then WGET=true; fi 
which curl >/dev/null 2>&1
if [ $? -eq 0 ]; then CURL=true; fi 

if [ $WGET = false ] && [ $CURL = false ]
then
    echo "This script needs wget or curl to be installed on your system">&2
    exit 1
fi 
WGET=false
export WGET CURL #  Must export for the subshell

### A unique string to name temporary files
fbase=$(basename $tilelist)
fbase=${fbase}.$datebeg.$dateend

### Build up the query.
### The base for search.
### collection_concept_id for HLS v2.0, both L30 and S30.

### Parse metadata to get a list of files to download.
### Export the filelist variable for subshells.
### Sort file names for humans.

if [ $RERUN_MODE = true ]
then
    if [ ! -f "$tilelist" ] || [ ! -s "$tilelist" ]
    then
        echo ""
        echo "All previously failed files have been downloaded successfully."
        exit 0
    fi
    echo "Re-run mode: using $tilelist as the file list directly"
    # Copy to a temp file BEFORE clearing FAILREPORT — in re-run mode tilelist IS
    # failed_downloads.txt, so we must read it before wiping it.
    ALLFILELIST=/tmp/hls.rerun.flist.${USER}.$$
    cp "$tilelist" "$ALLFILELIST"
    export ALLFILELIST
else
    ALLFILELIST=/tmp/${fbase}.down.flist.txt.$USER.$$
    export ALLFILELIST
fi

### Clear the failure report so it only reflects the current run.
rm -f "$FAILREPORT"

if [ $RERUN_MODE = false ]
then
    querybase="https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C2021957295-LPCLOUD&collection_concept_id=C2021957657-LPCLOUD"
    ### Add date range
    querybase="${querybase}&temporal=${datebeg}T00:00:00Z,${dateend}T23:59:59Z"

    ### Other possible parameters.
    querybase="${querybase}&attribute=int,SPATIAL_COVERAGE,$SPATIAL,"   # min
    querybase="${querybase}&attribute=int,CLOUD_COVERAGE,,$CLOUD"       # max. type has been changed from float to int. (4/25/2022)

    ### Query the metadata with pagination.
    meta=/tmp/${fbase}.down.meta.txt.$USER.$$
    >$meta

    onequery=/tmp/$fbase.single.query.$USER     # the return from one query in pagination.

    echo "Searching CMR ......"
    for tile in $(cat $tilelist)
    do
        # A rough check if the tile ID is valid
        case $tile in
          [0-6][0-9][A-Z][A-Z][A-Z]);;
          *) echo "Not a valid 5-character tile ID, ignore: $tile" >&2;
                 continue;;
        esac

        # Note: do not make wget quite (-q) and curl silent (-s); instead display any error message. 12/1/2022
        psize=200   # A small page size to test pagination.  This many granules (not files within a granule)  per page.
        if [ $WGET = true ]
        then
            pnum=1
            while :
            do
                query="${querybase}&attribute=string,MGRS_TILE_ID,$tile&page_size=$psize&page_num=$pnum"
                wget --timeout=60 --tries=1 "$query" -O $onequery
                if ! grep -q '"entry"' $onequery; then break; fi      # no valid CMR response
                if grep -q '"entry":\[\]' $onequery; then break; fi   # empty page, done
                cat $onequery >>$meta
                pnum=$((pnum+1))
            done
        else
            pnum=1
            while :
            do
                query="${querybase}&attribute=string,MGRS_TILE_ID,$tile&page_size=$psize&page_num=$pnum"
                curl -s --max-time 60 "$query" >$onequery
                if ! grep -q '"entry"' $onequery; then break; fi      # no valid CMR response
                if grep -q '"entry":\[\]' $onequery; then break; fi   # empty page, done
                cat $onequery >>$meta
                pnum=$((pnum+1))
            done
        fi
    done

    # Example granule name:
    #   HLS.L30.T18SUJ.2025183T155159.v2.0
    # Download the granules chronologically, i.e., sort on the 3rd and 4th fields in the granule name
    nprefix=9   # Skip so many characters to sort on the 3rd and 4th fields. A value in 6,7,8 has this effect as well.

    tr "," "\n" < $meta  |
      grep https |                              # ignore the s3 links
      egrep "/HLS.[LS]30." |                    # granule names
      tr "\"" " " |
      awk '{print $(NF-1)}' |                   # the full https link
      awk -F"/" '{print $NF, $0}' |
      sort -k1.$nprefix |                       # sort from this column of filename on
      awk '{print $2}' >$ALLFILELIST
fi

### Download a single file to a temp path and rename to final name on success.
### Returns 0 on success, 1 on failure.
function download_file()
{
    local url=$1
    local outdir=$2
    local cookie=$3

    local fname
    fname=$(basename "$url")
    local tmpfile="$outdir/.tmp.$fname"
    local finalfile="$outdir/$fname"

    rm -f "$tmpfile"

    # CONN_TIMEOUT: seconds to wait for the initial connection
    # STALL_TIMEOUT: seconds allowed with no data received before aborting
    # MAX_TIME: hard ceiling on total time per file (covers stalled TCP connections)
    local CONN_TIMEOUT=30
    local STALL_TIMEOUT=60
    local MAX_TIME=600

    if [ $WGET = true ]
    then
        wget -q --timeout=$STALL_TIMEOUT --tries=1 --connect-timeout=$CONN_TIMEOUT "$url" -O "$tmpfile"
        exitcode=$?
    else
        curl --cookie-jar "$cookie" -n -s -L \
             --connect-timeout $CONN_TIMEOUT \
             --speed-limit 1 --speed-time $STALL_TIMEOUT \
             --max-time $MAX_TIME \
             --output "$tmpfile" "$url"
        exitcode=$?
    fi

    if [ $exitcode -ne 0 ]
    then
        rm -f "$tmpfile"
        return 1
    fi

    mv "$tmpfile" "$finalfile"
    return 0
}
export -f download_file

### Download all files for a granule, one file at a time with temp-file safety.
### If a granule directory already exists and is complete, skip it.
### Retries each file up to MAX_ATTEMPTS times. On total failure, records URLs
### to the shared FAILREPORT for re-run.
function download_granule()
{
    local granule=$1

    set -u
    set -o pipefail
    USER=${USER:-$(id -un 2>/dev/null || echo "user")}

    # Build the output directory path from the granule name fields.
    # HLS.S30.T18SUJ.2025182T155819.v2.0 -> type=S30, tileid=18SUJ, year=2025
    local gtype gtileid gyear
    gtype=$(  echo "$granule" | awk -F'.' '{print $2}')
    gtileid=$(echo "$granule" | awk -F'.' '{print substr($3,2,5)}')
    gyear=$(  echo "$granule" | awk -F'.' '{print substr($4,1,4)}')

    local subdir="${gtileid:0:2}/${gtileid:2:1}/${gtileid:3:1}/${gtileid:4:1}"
    local outdir="$OUTDIR/$gtype/$gyear/$subdir/$granule"

    # Collect the URLs for this granule (anchored match to avoid substring collisions).
    local filesInGranule="/tmp/tmp.files.in.${granule}.txt.${USER}"
    grep "/${granule}/" "$ALLFILELIST" > "$filesInGranule"

    mkdir -p "$outdir"
    local cookie="/tmp/tmp.cookie.${granule}.${USER}"
    trap 'echo "Interrupted, cleaning up $outdir"; rm -rf "$outdir"; rm -f "$filesInGranule" "$cookie"; exit 1' HUP INT TERM

    local MAX_ATTEMPTS=3
    local granule_failed=0   # set to 1 if any file in the granule fails

    while IFS= read -r url
    do
        [ -z "$url" ] && continue
        local fname
        fname=$(basename "$url")

        if [ -f "$outdir/$fname" ]
        then
            echo "Skipping $fname (already exists)"
            continue
        fi

        local attempt=0
        local file_ok=1

        while [ $attempt -lt $MAX_ATTEMPTS ]
        do
            attempt=$((attempt + 1))
            echo "Downloading $fname (attempt $attempt of $MAX_ATTEMPTS)"
            download_file "$url" "$outdir" "$cookie"
            if [ $? -eq 0 ]
            then
                file_ok=0
                break
            fi
            echo "......Failed to download $fname (attempt $attempt of $MAX_ATTEMPTS)" >&2
        done

        if [ $file_ok -ne 0 ]
        then
            echo "......All $MAX_ATTEMPTS attempts failed for $fname" >&2
            echo "$url" >> "$FAILREPORT"
            granule_failed=1
        fi
    done < "$filesInGranule"

    rm -f "$cookie"

    if [ $granule_failed -ne 0 ]
    then
        echo "......Granule $granule incomplete." >&2
    else
        echo "Finished $granule"
    fi

    rm -f "$filesInGranule"
}
export -f download_granule

### Run $NP bash subshells
if [ $RERUN_MODE = true ]
then
    ng=$(wc -l < $ALLFILELIST | awk '{print $1}')
    echo -e "\nRe-running $ng failed file(s)."
    # Derive unique granule names from the failed URLs and re-download
    awk -F"/" '{print $NF}' $ALLFILELIST |
        sed 's/\.[^.]*\.[^.]*$//' |
        sort -u |
        xargs -P $NP -I% bash -c "download_granule %"
else
    ng=$(grep B01 $ALLFILELIST | wc -l | awk '{print $1}')
    if [ $ng -eq 0 ]
    then
        echo -e "\nThe search found 0 granules."
        echo "NOTE: If you expected results, CMR may be temporarily unavailable or experiencing issues."
        echo "      Check https://status.earthdata.nasa.gov and retry if needed."
    else
        echo -e "\nThe search found $ng granules. Going through the granules now, and"
        echo "      granules previously downloaded with integrity will be skipped."
        grep B01 $ALLFILELIST |
            xargs -I%  basename % .B01.tif |        # Get each granule name from its B01 filename
            xargs -P $NP -I% bash -c "download_granule %"   # run $NP processes to download
    fi
fi

if [ $RERUN_MODE = false ]; then
    rm -f $meta $onequery
fi
rm -f $ALLFILELIST

if [ -f "$FAILREPORT" ] && [ -s "$FAILREPORT" ]
then
    echo ""
    echo "Some files failed to download. Failed URLs saved to:"
    echo "    $FAILREPORT"
    echo ""
    echo "NOTE: Re-run the script to retrieve the missing files:"
    echo "    $0 $FAILREPORT $OUTDIR"
else
    rm -f "$FAILREPORT"
    echo ""
    if [ $ng -eq 0 ]; then
        echo "No granules found for the given parameters."
    elif [ $RERUN_MODE = true ]; then
        echo "All previously failed files have been downloaded successfully."
    else
        echo "All granules downloaded successfully."
    fi
fi

exit 0
