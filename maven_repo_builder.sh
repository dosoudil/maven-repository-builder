#!/bin/bash

# defaults
METADATA=false
REPO_DIR="./maven-repository"
DOWNLOADER_DIR="../maven-repository-builder/"

# =======================================
# ====== reading command arguments ======
# =======================================
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
    echo "No config file specified."
    echo 'Usage: -c CONFIG_FILENAME [-r REPO_FILENAME] [-t REPO_DIR] [-m] [-d DOWNLOADER_DIR]'
    exit 1
fi

# ================================================
# == 1. and 2. - create GAV list and filter it ===
# ================================================
FILELIST=`mktemp XXXXXX.tmp`
python maven_repo_builder.py -c ${CONFIG} > ${FILELIST}
if test $? != 0; then
    echo "Creation of artifact lists failed."
    exit 1
fi

# ================================================
# ============== 3. fetch artifacts ==============
# ================================================
cat ${FILELIST} | while read $LINE; do
    URL=`split '   ' {print $1}`
    ARTIFACT_LIST_FILE=`split ' ' {print $2}`
    python ${DOWNLOADER_DIR}maven_repo_builder.py -o ${REPO_DIR} -u ${URL} ${ARTIFACT_LIST_FILE}
    if test $? != 0; then
        echo "Download of artifacts listed in '${ARTIFACT_LIST_FILE}' from '${URL}' failed."
        exit 1
    fi
    rm ${ARTIFACT_LIST_FILE}
done
rm ${FILELIST}

# ================================================
# == 4. generate metadata (opt), zip repo (opt) ==
# ================================================
#if ${METADATA}; then
#    refreshMetadata(${REPO_DIR})
#fi
if [ ! -z ${REPO_FILE} ]; then
    zip -qr ${REPO_FILE} ${REPO_DIR}
fi
