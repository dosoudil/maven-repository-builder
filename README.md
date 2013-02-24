Maven Repository Builder
========================

Build a Maven repository from a list of dependencies and the URL to an existing repository.

    Usage: maven_repo_builder.py [-h] [-u URL] [-d DIRECTORY] [-l LIST]

    Generate a Maven repository.

    Options:
      -h, --help            show this help message and exit
      -d DEBUG, --debug=DEBUG
                            Set the level of log output.  Can be set to debug,
                            info, warning, error, or critical
      -u URL, --url=URL     URL of the remote repository from which artifacts are
                            downloaded
      -o OUTPUT, --output=OUTPUT
                            Local output directory for the new repository
      -l LIST, --list=LIST  The path to the file containing the list of
                            dependencies to download


