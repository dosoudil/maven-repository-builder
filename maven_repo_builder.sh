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
else
    # creation of list of parameters passed to the python script
    MRB_PARAMS=()
    if [[ ! -z ${CONFIG} ]]; then
        MRB_PARAMS+=("-c")
        MRB_PARAMS+=(${CONFIG})
    fi
    if [[ ! -z ${URL} ]]; then
        MRB_PARAMS+=("-u")
        MRB_PARAMS+=(${URL})
    fi
    if [[ ! -z ${CLASSIFIERS} ]]; then
        MRB_PARAMS+=("-a")
        MRB_PARAMS+=(${CLASSIFIERS})
    fi
    if [[ ! -z ${OUTPUT_DIR} ]]; then
        MRB_PARAMS+=("-o")
        MRB_PARAMS+=(${OUTPUT_DIR})
    fi
    if [[ ! -z ${LOGLEVEL} ]]; then
        MRB_PARAMS+=("-l")
        MRB_PARAMS+=(${LOGLEVEL})
    fi

    # skip all named parameters and leave just unnamed ones (filenames)
    if [ $# -gt 0 ]; then
        while [ $# -gt 0 ] && [ ${1:0:1} = '-' ]; do
            if [ ${1:1:2} = 'c' ] || [ ${1:1:2} = 'r' ] || [ ${1:1:2} = 'a' ] || [ ${1:1:2} = 'o' ] || [ ${1:1:2} = 'u' ] || [ ${1:1:2} = 'l' ]; then
                shift
            fi
            shift
        done
    fi

    while [ $# -gt 0 ]; do
        MRB_PARAMS+=("${1}")
        shift
    done

    python maven_repo_builder.py "${MRB_PARAMS[@]}"
    if test $? != 0; then
        echo "Creation of repository failed."
        exit 1
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
