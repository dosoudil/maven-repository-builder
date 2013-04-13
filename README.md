Maven Repository Builder
========================

Build a Maven repository from a list of dependencies and the URL to an existing repository.
This tool requires python 2.6 or higher.

Basic Usage
-----------

    Usage: maven_repo_builder.py [-h] [-u URL] [-l ARTIFACT_LIST] [-o OUTPUT_DIRECTORY]

    Generate a Maven repository.

    Options:
      -h, --help            show this help message and exit
      -l LOGLEVEL, --loglevel=LOGLEVEL
                            Set the level of log output.  Can be set to debug,
                            info, warning, error, or critical
      -u URL, --url=URL     URL of the remote repository from which artifacts are
                            downloaded
      -f FILE, --file=FILE  The path to the file containing the list of artifacts
                            to download
      -o OUTPUT, --output=OUTPUT
                            Local output directory for the new repository

Example Repository List
-----------------------
[Example Repository List](https://github.com/jboss-eap/maven-repository-builder/blob/master/example-config/artifact-list.txt)


Compare Repositories
--------------------
A script is also included which can be used to compare two repositories to see if they
contain matching GAVs (artifacts with the same groupId, artifactId, and version).

    Usage: compare_repositories.py [options] REPOSITORY_PATH

    Compare a local Maven repository to a remote repository.

    Options:
      -h, --help            show this help message and exit
      -l LOGLEVEL, --loglevel=LOGLEVEL
                            Set the level of log output.  Can be set to debug,
                            info, warning, error, or critical
      -u URL, --url=URL     URL of the remote repository to use for comparison







