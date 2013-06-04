#!/bin/bash

# defaults
METADATA=false
REPO_DIR="local-maven-repository"
LOGLEVEL="info"

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
        l) LOGLEVEL=${OPTARG};;
    esac
done

if [ -z ${CONFIG} ]; then
    echo "No config file specified."
    echo 'Usage: -c CONFIG_FILENAME [-r REPO_FILENAME] [-t REPO_DIR] [-m]'
    exit 1
fi

# ================================================
# ============== 1. create GAV list ==============
# ============== 2. filter the list ==============
# ============== 3. fetch artifacts ==============
# ================================================
if [ -z ${REPO_DIR} ]; then
    python maven_repos_builder.py -c ${CONFIG} -l ${LOGLEVEL}
    if test $? != 0; then
        echo "Creation of repository failed."
        exit 1
    fi
else
    python maven_repo_builder.py -c ${CONFIG} -l ${LOGLEVEL} -o ${REPO_DIR}
    if test $? != 0; then
        echo "Creation of repository failed."
        exit 1
    fi
fi

# ================================================
# == 4. generate metadata (opt), zip repo (opt) ==
# ================================================
#if ${METADATA}; then
#    refreshMetadata(${REPO_DIR})
#fi
if [ ! -z ${REPO_FILE} ]; then
    zip -qr ${REPO_FILE} ${REPO_DIR}
fi
