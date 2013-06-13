#!/usr/bin/env python

"""compare_repositories.py: Compare a local maven repository to a remote repository checking for GAV conflicts."""

import logging
import optparse
import os
import re
import sys
import tempfile

import maven_repo_util


def compareArtifacts(localRepoPath, remoteUrl):
    tempDownloadDir = tempfile.mkdtemp()
    regexChecksum = re.compile('(\.sha1$)|(\.md5$)')
    regexMetadata = re.compile('(maven-metadata.xml)|(\.lastUpdated$)|(_maven.repositories)')
    for root, dirs, files in os.walk(localRepoPath, followlinks=True):
        for filename in files:
            if regexChecksum.search(filename):
                continue
            if regexMetadata.search(filename):
                continue
            filepath = os.path.join(root, filename)
            relRepoPath = os.path.relpath(filepath, localRepoPath)
            logging.debug('Checking artifact: %s', relRepoPath)

            # Attempt to download remote artifact
            tempDownloadFile = os.path.join(tempDownloadDir, relRepoPath)
            remoteFileUrl = remoteUrl + "/" + relRepoPath
            maven_repo_util.download(remoteFileUrl, tempDownloadFile)

            # Compare the local and remote artifact checksums
            if os.path.exists(tempDownloadFile):
                localFileChecksum = maven_repo_util.getSha1Checksum(filepath)
                remoteFileChecksum = maven_repo_util.getSha1Checksum(tempDownloadFile)
                if (localFileChecksum != remoteFileChecksum):
                    logging.error('Checksums do not match for artifact %s', relRepoPath)
            else:
                logging.debug('File does not exist in remote repo: %s', relRepoPath)


def main():
    usage = "usage: %prog [options] REPOSITORY_PATH"
    cliOptParser = optparse.OptionParser(usage=usage, description='Compare a local Maven repository'
            ' to a remote repository.')
    cliOptParser.add_option('-l', '--loglevel',
            default='info',
            help='Set the level of log output.  Can be set to debug, info, warning, error, or critical')
    cliOptParser.add_option('-u', '--url',
            default='http://repo1.maven.org/maven2/',
            help='URL of the remote repository to use for comparison, defaults to Maven central')

    (options, args) = cliOptParser.parse_args()

    if (len(args) < 1):
        logging.error('Local repository path must be specified\n')
        cliOptParser.print_help()
        sys.exit()

    localRepoPath = args[0]

    # Set the log level
    maven_repo_util.setLogLevel(options.loglevel)

    # Read the list of dependencies
    if os.path.isfile(localRepoPath):
        logging.error('Local repository path is a file instead of a directory: %s', localRepoPath)
        sys.exit()
    elif not os.path.isdir(localRepoPath):
        logging.error('Local repository path must point to the root directory of a local maven repository: %s',
                localRepoPath)
        sys.exit()

    logging.info('Remote repository URL: %s', options.url)
    logging.info('Crawling local repository: %s', localRepoPath)
    compareArtifacts(localRepoPath, options.url)


if  __name__ == '__main__':
    main()
