#!/bin/bash

# defaults
METADATA=false
REPO_DIR="./maven-repository"
DOWNLOADER_DIR="../maven-repository-builder/"

# reading command arguments
while getopts "c:d:l:mr:t:" arg
do
    case "${arg}" in
        c) CONFIG=${OPTARG};;
        r) REPO_FILE=${OPTARG};;
        t) REPO_DIR=${OPTARG};;
        m) METADATA=true;;
        d) DOWNLOADER_DIR=${OPTARG};;
    esac
done

if [ -z ${CONFIG} ]; then
    if [ -z ${CONFIG} ]; then
        echo "No config file specified."
    fi
    echo 'Usage: -c CONFIG_FILENAME [-r REPO_FILENAME] [-t REPO_DIR] [-m] [-d DOWNLOADER_DIR]'
    exit 1
fi

# 1. and 2. - create GAV list and filter it
python maven_repo_builder.py -c ${CONFIG}
if test $? != 0; then
    echo "Creating of artifact lists failed."
    exit 1
fi

#while 