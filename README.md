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
        maven_repo_builder.sh -u URL  [-r REPO_FILENAME] [-m] [-o OUTPUT] [-a CLASSIFIERS] [-s CHECKSUM_MODE] [-d ADDITION] FILE...
        or
        maven_repo_builder.sh -c CONFIG [-r REPO_FILENAME] [-m] [-o OUTPUT] [-a CLASSIFIERS] [-s CHECKSUM_MODE] [-d ADDITION]

    Generate a Maven repository based on a file (or files) containing a list of artifacts.  Each list file must contain
    a single artifact per line in the format groupId:artifactId:fileType:<classifier>:version The example artifact list
    contains more information. Another usage is to provide Artifact List Generator configuration file.

    Options:
      -h                    show this help message and exit
      -c CONFIG
                            Configuration file to use to generate an artifact list
                            for the repository builder
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
      -s CHECKSUM_MODE
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


Artifact List Generator
-----------------------
The Artifact List Generator is a tool which handles generation of artifact list from specified sources. It is used by
maven_repo_builder.py or it can be used as a separate tool. Configuration structure is described below.

    Usage:
        artifact_list_generator.py -c CONFIG

    Generates an artifact list according to provided configuration. The output of the script is a list of repository
    URLs and artifacts separated by tab character per line. Every artifact is in format
    groupId:artifactId:fileType:version. The output is printed on stdout.

    Options:
      -h                    show this help message and exit
      -c CONFIG
                            Configuration file to use to generate an artifact list
                            for the repository builder
      -l LOGLEVEL
                            Set the level of log output.  Can be set to debug,
                            info, warning, error, or critical


Artifact List Generator Config
------------------------------
For an example config with full config structure see [Sample Config](https://github.com/jboss-eap/maven-repository-builder/blob/master/example-config/alg-config-sample.json)

### Basic configuration
*   **artifact-sources** - list of sources of artifacts which should be included in the produced repository
    *   **type** - one of the artifact source types:
        *   "mead-tag" - a MEAD tag which should be included; additional artifact source config fields for this type are:
            *   **tag-name** - the tag name.
            *   **koji-url** - URL of koji (Brew/MEAD) instance, usually
                ["http://brewhub.devel.redhat.com/brewhub/"](http://brewhub.devel.redhat.com/brewhub/).
            *   **download-root-url** - root URL from which build packages should be downloaded, usually
                ["http://download.devel.redhat.com/brewroot/packages/"](http://download.devel.redhat.com/brewroot/packages/).
            *   **included-gav-patterns-ref** - reference to a file, where are patterns of included GAVs, on every line
                should be single pattern. Stars are allowed to represent any string. Not required, if ommited, all
                found artifacts will be included.
        *   "dependency-list" - a merged lists of maven dependencies of selected GAVs; additional artifact source
            config fields for this type are
            *   **repo-url** - one repository URL or a list of them which should be searched.
            *   **top-level-gavs-ref** - reference to a file with the list of top level GAVs, every GAV should be on
                separate line.
        *   "repository" - a local or remote repository to crawl and include found artifacts; additional artifact
            source config fields for this type are
            *   **repo-url** -one repository URL or a list of them, which should be crawled
            *   **included-gav-patterns-ref** - the same as the corresponding MEAD tag's field


### Advanced config
*   **include-high-priority** and **include-low-priority** - includes another config file, which values will be
    overwritten by curernt config or in case of lists they will be merged. If order in a list matters (like in
    **artifact-sources**) then the items from the included file will be added before and after for high and low
    priority includes respectively. Neither of them is required.
*   **excluded-gav-patterns-ref** - list of references to files with list of top GAV patterns to be excluded, every GAV
    pattern should be on separate line. Stars are allowed to represent any string. Not required.
*   **excluded-repositories** - list of repository URLs which will be searched for any artifact found in specified
    artifact sources and when found, the artifact will be disposed. Not required.
*   **single-version** - flag to forbid multiple versions of one groupId:artifactId, there can be allowed multiple
    versions for specific GAs by **multi-version-ga-patterns-ref**. Not required, default value is true.
*   **multi-version-ga-patterns-ref** - list of references to a files with lists of GA patterns (stars allowed) with
    permitted multiple versions. Not required, used only when **single-version** = "true".


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


Metadata Generator
------------------
There is a script used by Maven repository Builder for metadata generator. It can be used
separately from the builder.

    Usage: generate_maven_metadata.sh [REPOSITORY_PATH]

    Generates metadata in specified directory. If none is specified then current workdir is used.


