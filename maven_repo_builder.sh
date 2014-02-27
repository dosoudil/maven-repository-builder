#!/bin/bash

help ()
{
    echo 'Usage: '"$1"' -u URL [-r REPO_FILENAME] [-o OUTPUT] [-b OUTPUT_REPO] [-m] [-l LOGLEVEL] [-d ADDITION] FILE...'
    echo 'Usage: '"$1"' -c CONFIG [-r REPO_FILENAME] [-o OUTPUT] [-b OUTPUT_REPO] [-m] [-l LOGLEVEL] [-d ADDITION]'
    echo 'Usage: '"$1"' -h'
    echo ''
    echo 'Options:'
    echo '  -h                    show this help message and exit'
    echo '  -c CONFIG'
    echo '                        Configuration file to use for generation of an'
    echo '                        artifact list for the repository builder'
    echo '  -u URL'
    echo '                        Comma-separated list of URLs of the remote repositories from'
    echo '                        which artifacts are downloaded. It is used along with artifact'
    echo '                        list files when no config file is specified.'
    echo '  -o OUTPUT'
    echo '                        Local output directory for the new repository. By default'
    echo '                        "local-maven-repository" will be used.'
    echo '  -b OUTPUT_REPO'
    echo '                        Name of directory in which will be the artifracts'
    echo '                        contained in the output direcotry. It can be empty or'
    echo '                        multi-level path, e.g. path/to/repo. Defaults to'
    echo '                        "maven-repository".'
    echo '  -a CLASSIFIERS'
    echo '                        Colon-separated list of additional classifiers to download.'
    echo '                        By default "sources" will be used. There can be a type specified '
    echo '                        with each classifiers separated by colon, e.g. jar:sources.'
    echo '                        The old way of separation of classifiers by colon is deprecated.'
    echo '  -r REPO_FILENAME'
    echo '                        Zip the created repository in a file with provided name'
    echo '  -s CHECKSUM_MODE'
    echo '                        Mode of dealing with MD5 and SHA1 checksums. Possible options are:'
    echo '                        generate - generates the checksums (default)'
    echo '                        download - download the checksums if available, if not, generates them'
    echo '                        check - checks if downloaded and generated checksums are equal'
    echo '  -x EXCLUDED_TYPES'
    echo '                        Colon-separated list of filetypes to exclude. Defaults to '
    echo '                        zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z.'
    echo '  -w GATCV_WHITELIST'
    echo '                        Name of a file containing GATCV patterns allowing usage of stars'
    echo '                        or regular expressions when enclosed in "r/pattern/". It can force'
    echo '                        inclusion of artifacts with excluded types.'
    echo '  -m'
    echo '                        Generate metadata in the created repository'
    echo '  -l LOGLEVEL'
    echo '                        Set the level of log output.  Can be set to debug,'
    echo '                        info, warning, error, or critical'
    echo '  -L LOGFILE'
    echo '                        Set the file in which the log output should be written'
    echo '  -d ADDITION'
    echo '                        Directory containing additional files for the repository.'
    echo '                        Content of directory ADDITION will be copied to the repository.'
    echo ''
}

isvarset()
{
    local v="$1"
    [[ ! ${!v} && ${!v-unset} ]] && return 1 || return 0
}

if [ $# -lt 1 ]; then
    help $0
    exit 1
fi

WORKDIR=$(cd $(dirname $0) && pwd)

# defaults
HELP=false
METADATA=false
OUTPUT_DIR="local-maven-repository"
OUTPUT_REPO="maven-repository"

# =======================================
# ====== reading command arguments ======
# =======================================
while getopts hc:u:r:a:o:b:l:L:s:x:w:md: OPTION
do
    case "${OPTION}" in
        h) HELP=true;;
        c) CONFIG=${OPTARG};;
        u) URL=${OPTARG};;
        r) REPO_FILE=${OPTARG};;
        a) CLASSIFIERS=${OPTARG};;
        s) CHECKSUM_MODE=${OPTARG};;
        x) EXCLUDED_TYPES=${OPTARG};;
        w) GATCV_WHITELIST=${OPTARG};;
        o) OUTPUT_DIR=${OPTARG};;
        b) OUTPUT_REPO=${OPTARG};;
        m) METADATA=true;;
        l) LOGLEVEL=${OPTARG};;
        L) LOGFILE=${OPTARG};;
        d) ADDITION=${OPTARG};;
    esac
done

if [ -z $OUTPUT_REPO ]; then
    OUTPUT_REPO_DIR=$OUTPUT_DIR
else
    OUTPUT_REPO_DIR=$OUTPUT_DIR/$OUTPUT_REPO
fi

if ${HELP}; then
    help $0
    exit
fi

# ================================================
# ============== 1. create GAV list ==============
# ============== 2. filter the list ==============
# ============== 3. fetch artifacts ==============
# ================================================

# creation of list of parameters passed to the python script
MRB_PARAMS=()
isvarset CONFIG && MRB_PARAMS+=("-c") && MRB_PARAMS+=("${CONFIG}")
isvarset URL && MRB_PARAMS+=("-u") && MRB_PARAMS+=("${URL}")
isvarset CLASSIFIERS && MRB_PARAMS+=("-a") && MRB_PARAMS+=("${CLASSIFIERS}")
isvarset OUTPUT_REPO_DIR && MRB_PARAMS+=("-o") && MRB_PARAMS+=("${OUTPUT_REPO_DIR}")
isvarset CHECKSUM_MODE && MRB_PARAMS+=("-s") && MRB_PARAMS+=("${CHECKSUM_MODE}")
isvarset EXCLUDED_TYPES && MRB_PARAMS+=("-x") && MRB_PARAMS+=("${EXCLUDED_TYPES}")
isvarset GATCV_WHITELIST && MRB_PARAMS+=("-w") && MRB_PARAMS+=("${GATCV_WHITELIST}")
isvarset LOGLEVEL && MRB_PARAMS+=("-l") && MRB_PARAMS+=("${LOGLEVEL}")
isvarset LOGFILE && MRB_PARAMS+=("-L") && MRB_PARAMS+=("${LOGFILE}")

# skip all named parameters and leave just unnamed ones (filenames)
if [ $# -gt 0 ]; then
    while [ $# -gt 0 ] && [ ${1:0:1} = '-' ]; do
        L=${1:1:2}
        if [ $L = 'c' ] || [ $L = 'r' ] || [ $L = 'a' ] || [ $L = 'o' ] || [ $L = 'b' ] || [ $L = 'u' ] || [ $L = 's' ] || [ $L = 'x' ] || [ $L = 'w' ] || [ $L = 'l' ] || [ $L = 'L' ] || [ $L = 'd' ] ; then
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

# ================================================
# == 4. generate metadata (opt), zip repo (opt) ==
# ================================================
if [ -d "$ADDITION" ]; then
    cp -rf $ADDITION/. ${OUTPUT_DIR}
fi
if ${METADATA}; then
    $WORKDIR/generate_maven_metadata.sh ${OUTPUT_REPO_DIR}
fi
if [ ! -z ${REPO_FILE} ]; then
    REPO_FILE_DIR=$(dirname ${REPO_FILE})
    if [ ! -d "${REPO_FILE_DIR}" ]; then
        mkdir -p "${REPO_FILE_DIR}"
    fi
    ABS_REPO_FILE=$(cd "${REPO_FILE_DIR}" && pwd -P)/$(basename ${REPO_FILE})
    cd `dirname ${OUTPUT_DIR}`
    zip -qr ${ABS_REPO_FILE} $(basename ${OUTPUT_DIR})
    cd $WORKDIR
fi
