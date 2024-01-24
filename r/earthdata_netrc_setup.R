# Required packages for this script
packages = c('sys', 'getPass')

# Identify missing (not installed) packages
new.packages = packages[!(packages %in% installed.packages()[,"Package"])]

# Install missing packages
if(length(new.packages)) install.packages(new.packages, repos='http://cran.rstudio.com/')

# Load packages into R
library(sys)
library(getPass)

# Specify path to user profile 
up <- file.path(Sys.getenv("USERPROFILE"))                            # Retrieve user directory (for netrc file)

# Below, HOME and Userprofile directories are set.  

if (up == "") {
    up <- Sys.getenv("HOME") 
    Sys.setenv("userprofile" = up)
    if (up == "") {
        cat('USERPROFILE/HOME directories need to be set up. Please type sys.setenv("HOME" = "YOURDIRECTORY") or  sys.setenv("USERPROFILE" = "YOURDIRECTORY") in your console and type your USERPROFILE/HOME direcory instead of "YOURDIRECTORY". Next, run the code chunk again.')
    }
} else {Sys.setenv("HOME" = up)}        

netrc_path <- file.path(up, ".netrc", fsep = .Platform$file.sep)    # Path to netrc file

# Create a netrc file if one does not exist already
if (file.exists(netrc_path) == FALSE || grepl("urs.earthdata.nasa.gov", readLines(netrc_path)) == FALSE) {
    netrc_conn <- file(netrc_path)
    
    # User will be prompted for NASA Earthdata Login Username and Password below
    writeLines(c("machine urs.earthdata.nasa.gov",
                 sprintf("login %s", getPass(msg = "Enter NASA Earthdata Login Username \n (An account can be Created at urs.earthdata.nasa.gov):")),
                 sprintf("password %s", getPass(msg = "Enter NASA Earthdata Login Password:"))), netrc_conn)
    close(netrc_conn)
}else{
    i <- 0 
    for (f in readLines(netrc_path)){
        i <- i + 1
        if (f =="machine urs.earthdata.nasa.gov"){
            username <- strsplit(readLines(netrc_path)[i+1], " ")[[1]][2]
            un <- getPass(msg = paste0("Is your NASA Earthdata Login Username: ", username, "\n\n Type yes or no."))
            if (tolower(un) == 'yes'){
                tx <- gsub(readLines(netrc_path)[i+2], sprintf("password %s", getPass(msg = "Enter NASA Earthdata Login Password:")), readLines(netrc_path))
                writeLines(tx, netrc_path)
                rm(username, un, tx, f, i)
            }else{
                user <- gsub(readLines(netrc_path)[i+1], sprintf("login %s", getPass(msg = "Enter NASA Earthdata Login Username:")), readLines(netrc_path))
                tx <- gsub(readLines(netrc_path)[i+2], sprintf("password %s", getPass(msg = "Enter NASA Earthdata Login Password:")), readLines(netrc_path))
                writeLines(tx, netrc_path)
                rm(username, un, user, tx, f, i)
            
            }
            break
        }
    }
}

