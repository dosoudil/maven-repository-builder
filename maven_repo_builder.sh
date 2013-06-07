#!/bin/bash

help ()
{
    echo 'Usage: [-h] [-r REPO_FILENAME] [-o OUTPUT_DIR] [-m] [-l LOGLEVEL] [-c CONFIG_FILENAME] [-u URL] [FILE...]'
    echo ''
    echo 'Options:'
    echo '  -h                    show this help message and exit'
    echo '  -c CONFIG'
    echo '                        Configuration file to use for generation of an'
    echo '                        artifact list for the repository builder'
    echo '  -u URL'
    echo '                        URL of the remote repository from which artifacts are'
    echo '                        downloaded. It is used along with artifact list files'
    echo '                        when no config file is specified.'
    echo '  -o OUTPUT'
    echo '                        Local output directory for the new repository. By default'
    echo '                        "local-maven-repository" will be used.'
    echo '  -a CLASSIFIERS'
    echo '                        Comma-separated list of additional classifiers to download.'
    echo '                        By default "sources" will be used.'
    echo '  -r REPO_FILENAME'
    echo '                        Zip the created repository in a file with provided name'
    echo '  -m'
    echo '                        Generate metadata in the created repository'
    echo '  -l LOGLEVEL'
    echo '                        Set the level of log output.  Can be set to debug,'
    echo '                        info, warning, error, or critical'
    echo ''
}


# defaults
HELP=false
METADATA=false
LOGLEVEL="info"
CLASSIFIES="sources"

# =======================================
# ====== reading command arguments ======
# =======================================
while getopts hc:u:r:a:o:l:m OPTION
do
    case "${OPTION}" in
        h) HELP=true;;
        c) CONFIG=${OPTARG};;
        u) URL=${OPTARG};;
        r) REPO_FILE=${OPTARG};;
        a) CLASSIFIERS=${OPTARG};;
        o) OUTPUT_DIR=${OPTARG};;
        m) METADATA=true;;
        l) LOGLEVEL=${OPTARG};;
    esac
done

# ================================================
# ============== 1. create GAV list ==============
# ============== 2. filter the list ==============
# ============== 3. fetch artifacts ==============
# ================================================
if ${HELP}; then
    help
elif [ -z ${CONFIG} ]; then
    if [ ! -z $1 ]; then
        while [ ${1:0:1} = '-' ]; do
            if [ ${1:1:2} = 'c' ] || [ ${1:1:2} = 'r' ] || [ ${1:1:2} = 'a' ] || [ ${1:1:2} = 'o' ] || [ ${1:1:2} = 'u' ] || [ ${1:1:2} = 'l' ]; then
                shift
            fi
            shift
        done
    fi

    if [ -z ${URL} ]; then
        echo "No config file neither URL specified."
        echo ''
        help
        exit 1
    elif [ -z ${OUTPUT_DIR} ]; then
        python maven_repo_builder.py -u ${URL} -a "${CLASSIFIERS}" -l ${LOGLEVEL} "$@"
    else
        python maven_repo_builder.py -o ${OUTPUT_DIR} -u ${URL} -a "${CLASSIFIERS}" -l ${LOGLEVEL} "$@"
    fi
else
    if [ -z ${OUTPUT_DIR} ]; then
        python maven_repo_builder.py -c ${CONFIG} -a "${CLASSIFIERS}" -l ${LOGLEVEL}
        if test $? != 0; then
            echo "Creation of repository failed."
            exit 1
        fi
    else
        python maven_repo_builder.py -c ${CONFIG} -o ${OUTPUT_DIR} -a "${CLASSIFIERS}" -l ${LOGLEVEL}
        if test $? != 0; then
            echo "Creation of repository failed."
            exit 1
        fi
    fi
fi

# ================================================
# == 4. generate metadata (opt), zip repo (opt) ==
# ================================================
#if ${METADATA}; then
#    refreshMetadata(${OUTPUT_DIR})
#fi
if [ ! -z ${REPO_FILE} ]; then
    zip -qr ${REPO_FILE} ${OUTPUT_DIR}
fi
