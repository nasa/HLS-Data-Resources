#!/bin/bash 

# A bash script to download HLS data from LP DAAC. It runs on an OS where 
# bash is available: Linux, Mac, (some Windows as well?). An account on 
# urs.earthdata.nasa.gov is required. 
#
# Features include:
#   1) Query the DAAC metadata based on tile ID, date range, cloud cover,
#      spatial cover, etc, to get a list of HLS files for downloading
#   2) Organize the HLS files into subdirectories based on data type (L30/S30), 
#      year, tile ID, and granule name
#   3) Run multiple download processes in parallel 
#   4) A second invocation won't download files that have been downloaded before,
#      so similar to rsync.
#
# Commandline paramaeters:
#   $1: a text file of tile IDs
#   $2: start of the sensing date
#   $3: end of the sensing date, inclusive
#   $4: the base directory of output; subdirectories are to be created in it.  
#
# Implementation notes: 
#    1) The metadata query result can be returned in either xml or json format. 
#       Json format gives the data file paths directly, but the xml format needs a 
#       second query to find the data file paths.
#       This script chooses json.
#    2) The parameter NP in this script specifies how many download processes to run.
#       The default is 10; can be modifed based on the capacity of the local computer. 
#       Similarly, CLOUD_COVERAGE and SPATIAL_COVERAGE thresholds  are hard-coded to 
#	give all the data, but can be adjusted at the beginning of this script..
#    3) The DAAC script DAACDataDownload.py is not needed. As long as an entry in .netrc
#       file is set up for urs.earthdata.nasa.gov, wget/curl can be used in place of the 
#       DAAC script, which is described at 
# https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse
#    4) Both wget and curl can download multiple files in one invocation.
# 	They appear to be have the same speed.
#    5) Can be slow because of the use of bash and bash subshell.
#    6) Although the script will skip a file if the existing local copy appears to be 
#	identical to remote file, the time saving is not much, probably because there are 
#	so many files in a granule to check (time stamp, length)
#
# Junchang Ju. June 5, 2021
#              July 29, 2021

if [ $# -ne 4 ]
then
	echo "Usage: $0 <tilelist> <date_begin> <date_end> <out_dir>" >&2
	echo "where	<tilelist> is a text file of 5-character tile IDs" >&2
	echo "		<date_begin> and <date_end> are in the format 2021-12-31" >&2 
	echo "		<out_dir> is the base of output directory. Subdirectories are to be created within it " >&2 
	exit 1
fi
tilelist=$1
datebeg=$2
dateend=$3
OUTDIR=$4

### A few customizable parameter 
NP=10 		# Run this many download processes by default. 
CLOUD=100	# Maximum amount of cloud cover in %
SPATIAL=0	# Minimum amount of spatial cover in %


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

### Delete the tailing "/" if there is any.
OUTDIR=$(echo $OUTDIR | sed 's:/$::')   
export OUTDIR	# Must export for the subshell

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
export WGET CURL #  Must export for the subshell

### Force to use curl for speed comparison 
#WGET=false

### Create a string to name temporary files
fbase=tmp
for p in $1 $2 $3
do
	base=$(basename $p)
	fbase=${fbase}_$base
done

### Build up the query.
### The base for search. Both L30 and S30. Page size 2000 is big enough for a single tile 
### over the given time period; pagination not needed.
#query="https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C1711924822-LPCLOUD&collection_concept_id=C1711972753-LPCLOUD&page_size=2000"
query="https://cmr.earthdata.nasa.gov/search/granules.json?collection_concept_id=C2021957295-LPCLOUD&collection_concept_id=C2021957657-LPCLOUD&page_size=2000"
### Add date range
query="${query}&temporal=${datebeg}T00:00:00Z,${dateend}T23:59:59Z"

### Other possible parameters.
query="${query}&attribute[]=int,SPATIAL_COVERAGE,$SPATIAL,"		# min 
# query="${query}&attribute[]=float,CLOUD_COVERAGE,,$CLOUD" 		# max. There is an issue for data type for CLOUD_COVERAGE

### Add tile ID and begin query
meta=/tmp/${fbase}.down.meta.txt
>$meta
for tile in $(cat $tilelist)
do
	# A rough check if the tile ID is valid
	case $tile in
	  [0-6][0-9][A-Z][A-Z][A-Z]);;
	  *) echo "Not a valid 5-character tile ID, ignore: $tile" >&2;
             continue;;
	esac

	# Query twice for now: one for L30, one for S30 because of the inconsistency of data type.
	# Once the data type problem is resolved, one of the queries will no longer be needed.
	query_final="${query}&attribute[]=float,CLOUD_COVERAGE,,$CLOUD" 	# max 
	if [ $WGET = true ]
	then
		wget -q "${query_final}&attribute[]=string,MGRS_TILE_ID,$tile" -O - >>$meta
	else
		curl -s "${query_final}&attribute[]=string,MGRS_TILE_ID,$tile" >>$meta
	fi

	query_final="${query}&attribute[]=int,CLOUD_COVERAGE,,$CLOUD" 		# max 
	if [ $WGET = true ]
	then
		wget -q "${query_final}&attribute[]=string,MGRS_TILE_ID,$tile" -O - >>$meta
	else
		curl -s "${query_final}&attribute[]=string,MGRS_TILE_ID,$tile" >>$meta
	fi
done

### Parse metadata for a list of files to download. Export for subshell.
### Sort file names for humans.
flist=/tmp/${fbase}.down.flist.txt
export flist

tr "," "\n" < $meta  | 
  grep https |
  egrep "/HLS.[LS]30." | 
  tr "\"" " " |
  awk '{print $3}' |
  awk -F"/" '{print $NF, $0}' |
  sort -k1,1 |
  awk '{print $2}' >$flist

### A function to download all the files in a granule. The B01 file pathname 
### of the granule is given.  Save the granule in its own directory.
function download_granule()
{
	outdir=
	set -o pipefail
	trap 'rm -rf $outdir' 1 2 15

	# Example B01 basename: HLS.L30.T18SUJ.2021078T153941.v1.5.B01.tif
	fullpath=$1
	B1base=$(basename $fullpath)

	# Granule name and the all the files for this granule
	granule=$(echo $B1base | awk -F"." '{print $1 "." $2 "." $3 "." $4 "." $5 "." $6}')
	allfile=/tmp/tmp.files.in.${granule}.txt	# PWD for the later subshell for curl.
	grep $granule $flist > $allfile 

	# Output directory 
	set $(echo $B1base | awk -F"." '{ print $2, substr($3,2,5), substr($4,1,4)}')
	type=$1
	tileid=$2
	year=$3

	subdir=$(echo $tileid | awk '{print substr($0,1,2) "/" substr($0,3,1) "/" substr($0,4,1) "/" substr($0,5,1)}')
	outdir=$OUTDIR/$type/$year/$subdir/$granule
	mkdir -p $outdir

	# Cookie is needed by curl on my mac at least. Without it, only the jpg and json 
	# files in lp-prod-public are downloaded, but not the files in /lp-prod-protected/ 
	# on the DAAC server.
	cookie=/tmp/tmp.cookie.$granule

	echo "Downloading into $outdir"
	if [ $WGET = true ]
	then
		wget -q -N -i $allfile -P $outdir
		if [ $? -eq 0 ]
		then
			echo "Finished downloading into $outdir"
		else
			rm -rf $outdir
		fi
	else
		# Older curl does not have the option for output directory. So use subshell.
		# And curl does not take a list of URL; bad.
		# ( cd $outdir && cat $allfile | xargs -n1 curl -n -s -C -  -OL )
		( cd $outdir && cat $allfile | xargs curl --cookie-jar $cookie -n -s -L -C - --remote-name-all )
		if [ $? -eq 0 ]
		then
			echo "Finished downloading $outdir"
		else 
			rm -rf $outdir
		fi
		rm $cookie
	fi

	rm $allfile 
}
export -f download_granule

### Run $NP bash subshells
ng=$(grep B01 $flist | wc -l | awk '{print $1}')
echo "$ng granules to download"
grep B01 $flist | xargs -n1 -P $NP -I% bash -c "download_granule %"  

rm -f $meta $flist
exit 0
