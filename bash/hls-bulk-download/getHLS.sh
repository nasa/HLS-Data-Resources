#!/bin/bash 

# A bash script to download HLS V.20 data from LP DAAC. It runs on an OS where 
# bash is available: Linux, Mac, (some Windows as well?). An account on 
# urs.earthdata.nasa.gov is required. 
#
# The HLS products are saved in subdirectories of the specified output directory like
#   L30/2025/18/S/U/J/HLS.L30.T18SUJ.2025208T154620.v2.0/
#   S30/2025/18/S/U/J/HLS.S30.T18SUJ.2025219T154819.v2.0
#
# Features include:
#   1) Run multiple download processes in parallel 
#   2) Download with corruption detection. Delete the granule once file 
#      corruption is detected, and a second invocation of this script 
#      only download for the failed ones in the previous run.
#
# Command-line paramaeters:
#   $1: a text file of tile IDs of 5 characters
#   $2: start of the sensing date
#   $3: end of the sensing date, inclusive
#   $4: the parent directory of output; subdirectories are to be created in it.  
#
# Implementation notes: 
#    1) The metadata query result can be returned in either xml or json format. 
#       Choose json format because it gives the data file paths directly. 
#    2) The parameter NP in this script specifies how many parallel download processes 
#       to run.  The default is 10; can be modifed based on the capacity of the local computer. 
#       Similarly, CLOUD_COVERAGE and SPATIAL_COVERAGE thresholds  are hard-coded to 
#       give all the data, but can be adjusted at the beginning of this script..
#    3) Both wget and curl can download multiple files in one invocation.
#       They appear to be have the same speed.
#
# Additional implementation notes (12/1/2022):
#    4) curl on Centos (NCCS) does not accept the "[]" specification when the query
#       attribute specifies a range of value. 
#
#       For example:
#       query="${query}&attribute[]=int,SPATIAL_COVERAGE,$SPATIAL," 
#       would cause curl on Centos to return an exit code 3: 
#           [globbing] illegal character in range specification at pos xxx (some number)
#       although curl on MacOS accepts.
#
#       It turns out that range specifications with and without "[]" are both accepted
#       by wget, so do not use it at all.
#
# Junchang Ju.  June 5, 2021
#               July 29, 2021
#               April 3, 2026:  An overhaul. 1) Pagination in query was added, so the search would not limit
#                               to the max page_size 2000.
#                               2) Corruption detection in downloading was implemented. The size of each
#                               downloaded file is compared with the value reported in the cmr.xml file.
#                               If a comparision is not possible or the values do not match, it must be
#                               due to corruption. The corruption detection takes < 1 second. Delete
#                               the corrupted download granules. A second invocation will fill the gap,
#                               without redownload the healthy granules.
#

if [ $# -ne 4 ]
then
    echo "Usage: $0 <tilelist> <date_begin> <date_end> <out_dir>" >&2
    echo "where <tilelist> is a text file of 5-character tile IDs" >&2
    echo "      <date_begin> and <date_end> are in the format 2021-12-31" >&2 
    echo "      <out_dir> is the parent output directory, within which subdirectories are to be created" >&2 
    exit 1
fi
tilelist=$1
datebeg=$2
dateend=$3
OUTDIR=$4

set -u
set -o pipefail

### A few customizable parameter 
NP=10       # Run this many download processes by default. 
CLOUD=100   # Maximum amount of cloud cover in %
SPATIAL=0   # Minimum amount of spatial cover in %

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

### Check on date format
for d in $datebeg $dateend
do
    case $d in
      [12][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]);;
      *) echo "Given date $d not in the format 2021-12-31" >&2; exit 1;;
        esac      
done

### Delete the tailing "/" from the output directory name if there is any.
OUTDIR=$(echo $OUTDIR | sed 's:/$::')   
export OUTDIR   # Must export for the subshell

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
            wget  "$query" -O $onequery 
            if grep '"entry":\[\]' $onequery  >/dev/null        # Nothing to return
            then
                break
            fi

            cat $onequery >>$meta
            pnum=$((pnum+1))
        done
    else
        pnum=1
        while :
        do
            query="${querybase}&attribute=string,MGRS_TILE_ID,$tile&page_size=$psize&page_num=$pnum"
            curl  "$query"  >$onequery
            if grep '"entry":\[\]' $onequery  >/dev/null
            then
                break
            fi

            cat $onequery >>$meta
            pnum=$((pnum+1))
        done
    fi
done

### Parse metadata to get a list of files to download. 
### Export the filelist variable for subshells.
### Sort file names for humans.
ALLFILELIST=/tmp/${fbase}.down.flist.txt.$USER.$$
export ALLFILELIST

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

### Return 0 if the sizes of downloaded files and the reported sizes are the same;
### non-zero otherwise.  A check for possible download corruption, much faster than
### the robust checksum.
function same_filesize()
{
    # Two arguments. Granule name and its output directory
    local granule=$1
    local outdir=$2

    set -u  # The setting does not propagate from the main script.
    set -o pipefail

    # If interruption occurs in this function, simply exit, without deleting $outdir.
    trap 'exit 1 ' HUP INT TERM 

    ### File sizes reported in the CMR manifest file 
    expected_fsize=/tmp/expected.filesize.$granule.txt
    >$expected_fsize
    cmr=$outdir/$granule.cmr.xml
    if [ ! -f $cmr ]
    then
        return 1    # Clearly wrong, even CMR file is missing
    fi

    passcmr=/tmp/passcmr.$granule.txt
    tr "<>" "\n" <$cmr >$passcmr
    for hlsfile in $(cat $filesInGranule)
    do 
        base=$(basename $hlsfile)
        # Interestingly, the cmr.xml does not report its own file size
        case $base in
            $granule.cmr.xml) continue;;
        esac

        fsize=$(grep -A 9 "^$base" $passcmr | 
                    grep -A 2  "^SizeInBytes" | 
                    awk 'NR == 2' )

        if [ -z "$fsize" ]
        then
            return 1        # CMR itself is probably corrupted.
        fi
        echo $base $fsize >>$expected_fsize
    done    

    ### Check the size of each downloaded file 
    download_fsize=/tmp/downloaded.filesize.$granule.txt
    >$download_fsize
    for hlsfile in $(cat $filesInGranule)
    do 
        base=$(basename $hlsfile)

        # Interestingly, the cmr.xml does not report its own file size
        case $base in
            $granule.cmr.xml) continue;;
        esac

        fsize=$( ls -l $outdir/$base 2>/dev/null | awk '{print $5}' )
        if [ $? -ne 0 ] 
        then
            return 1            # Bail out.
        fi
        echo $base $fsize >>$download_fsize
    done

    ### Compare file size files
    diff $download_fsize $expected_fsize  >/dev/null 2>&1
    stat=$?
    rm $download_fsize  $expected_fsize 

    return $stat
}
export -f same_filesize

### A function to download all the files for the given granule. 
### If a granule has been downloaded before without corruption, skip. 
### If some corruption occurs during this download, the downloaded files 
### will be deleted; in this case, re-run the download script to make 
### another attempt.
function download_granule()
{
    # The only argument.
    # Example granule name
    # HLS.S30.T18SUJ.2025182T155819.v2.0
    granule=$1
    

    set -u  # The setting does not propagate from the main script.
    set -o pipefail

    # All the files in this granule
    filesInGranule=/tmp/tmp.files.in.${granule}.txt.${USER} 
    grep $granule $ALLFILELIST > $filesInGranule 

    # Buildup the output directory from the common parent directory.
    set $(echo $granule | awk -F"." '{ print $2, substr($3,2,5), substr($4,1,4)}')
    type=$1
    tileid=$2
    year=$3

    subdir=${tileid:0:2}/${tileid:2:1}/${tileid:3:1}/${tileid:4:1}
    outdir=$OUTDIR/$type/$year/$subdir/$granule

    # If the output directory exists, check its integrity
    if [ -d $outdir ]
    then
        same_filesize $granule $outdir 
        if [ $? = 0 ]
        then
            # A complete copy has been download before. No need to download again.
            return 0
        fi
    fi

    mkdir -p $outdir
    # Cookie is needed by curl on my mac at least. Without it, only the jpg and json 
    # files in lp-prod-public are downloaded, but not the files in /lp-prod-protected/ 
    # on the DAAC server.
    cookie=/tmp/tmp.cookie.$granule.$USER

    # Ready to download new granules or redownload corrupted granules. 
    trap 'echo Interruption occcurred, deleting $outdir; rm -rf $outdir; exit 1'  HUP INT TERM 
    echo "Downloading into $outdir" 
    if [ $WGET = true ]
    then
        TLIMIT=240
        timeout $TLIMIT wget -q -N -i $filesInGranule -P $outdir
        exitcode=$?
        if [ $exitcode -eq 0 ]
        then
            echo "Finished downloading into $outdir, now let's do quality check" >&2
        else
            echo "Wget with exit code $exitcode on $granule" 
            rm -rf $outdir
            return 1
        fi
    else
        # Curl does not take a list of URL; bad.
        # Older curl does not have the option for output directory. So use subshell.
        ( cd $outdir && cat $filesInGranule | xargs curl --cookie-jar $cookie -n -s -L -C - --remote-name-all )
        exitcode=$?
        if [ $? -eq 0 ] 
        then    
            echo "Finished downloading into $outdir, let's do quality check" >&2
        else 
            echo "Curl with exit code $exitcode on $granule" 
            rm -rf $outdir
            return 1 
        fi

        rm -f $cookie
    fi

    # The exit status from wget or curl is not reliable? (For curl, maybe because we're using a subshell?)
    # Let's check the integrity of the downloading.
    echo "......verifying file size for $granule "
    same_filesize $granule $outdir 
    if [ $? -ne 0 ]
    then
        echo "......Corruption detected in the downloaded files. Later need to rerun this script again. Deleting $outdir" >&2
        rm -rf $outdir
    fi

    rm -f $filesInGranule 
}
export -f download_granule

### Run $NP bash subshells
ng=$(grep B01 $ALLFILELIST | wc -l | awk '{print $1}')
echo -e "\nThe search found $ng granules. Going through the granules now, and"
echo "      granules previously downloaded with integrity will be skipped."

grep B01 $ALLFILELIST | 
    xargs -n1 -I%  basename % .B01.tif |        # Get each granule name from its B01 filename
    xargs -n1 -P $NP -I% bash -c "download_granule %"   # run $NP processes to download

rm -f $meta $ALLFILELIST $onequery

exit 0
