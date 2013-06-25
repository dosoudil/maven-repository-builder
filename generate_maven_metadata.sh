#!/bin/sh
WORKDIR=$(cd $(dirname $0) && pwd)

if [ -z $1 ]; then
    SEARCHDIR='.'
else
    SEARCHDIR=$1
fi

echo "Generating maven metadata files ..."
cd $SEARCHDIR
for d in $(find . -name \*.pom -print | sed -e "s:/[^/]*/[^/]*$::" | sort | uniq)
do
    python $WORKDIR/maven_metadata.py $d
done