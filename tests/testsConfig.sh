OUTPUTREPO=test-local-maven-repository
LOGGING=warning

run(){
   CONFIG=tests/config$1.json
   shift
   rm -rf $OUTPUTREPO
   echo "running: ./maven_repo_builder.sh -o $OUTPUTREPO -c $CONFIG -l $LOGGING $@"
   ./maven_repo_builder.sh -o $OUTPUTREPO -c $CONFIG -l $LOGGING "$@"
}


