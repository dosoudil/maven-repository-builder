Maven Repository Builder
========================

Build a Maven repository from a list of dependencies and the URL to an existing repository.
The list can be generated from defined sources like MEAD tag, remote/local repository or a
set of top level artifacts, which dependencies are included. This way there can be combined
several sources. Another way is to provide the artifact list in a file and call the builder
with single source URL. This tool requires python 2.6 or higher.

Basic Usage
-----------

    Usage:
        maven_repo_builder.sh -u URL  [-r REPO_FILENAME] [-m] [-o OUTPUT_DIRECTORY] FILE...
        or
        maven_repo_builder.sh -c CONFIG [-r REPO_FILENAME] [-m] [-o OUTPUT_DIRECTORY]

    Generate a Maven repository based on a file (or files) containing a list of
    artifacts.  Each list file must contain a single artifact per line in the
    format groupId:artifactId:fileType:<classifier>:version The example artifact
    list contains more information. Another usage is to provide Artifact List
    Generator configuration file. There is also sample configuration file in
    examples.

    Options:
      -h                    show this help message and exit
      -c CONFIG
                            Configuration file to use for generation of an
                            artifact list for the repository builder
      -u URL
                            URL of the remote repository from which artifacts are
                            downloaded. It is used along with artifact list files
                            when no config file is specified.
      -o OUTPUT
                            Local output directory for the new repository. By default
                            "local-maven-repository" will be used.
      -a CLASSIFIERS
                            Comma-separated list of additional classifiers to download.
                            By default "sources" will be used.
      -r REPO_FILENAME
                            Zip teh created repository in a file with provided name
      -s CHECKSUM_MODE'
                            Mode of dealing with MD5 and SHA1 checksums. Possible options are:
                            generate - generate the checksums (default)
                            download - download the checksums if available, if not, generate them
                            check - check if downloaded and generated checksums are equal
      -m
                            Generate metadata in the created repository
      -l LOGLEVEL
                            Set the level of log output.  Can be set to debug,
                            info, warning, error, or critical
      -d ADDITION
                            Directory containing additional files for the repository.
                            Content of directory ADDITION will be copied to the repository.


Example Repository List
-----------------------
For a description and examples of the format of the artifact list file, see
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







