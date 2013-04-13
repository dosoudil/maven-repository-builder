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
    for root, dirs, files in os.walk(localRepoPath):
         for filename in files:
             if regexChecksum.search(filename):
                 continue
             filepath = os.path.join(root, filename)
             relRepoPath = os.path.relpath(filepath, localRepoPath)
             logging.debug('Checking artifact: %s', relRepoPath)
             
             # get checksum of the local file
             localFileChecksum = maven_repo_util.getSha1Checksum(filepath)

             # get checksum of remote file
             tempDownloadFile = os.path.join(tempDownloadDir, relRepoPath)
             remoteFileUrl = remoteUrl + "/" + relRepoPath
             maven_repo_util.download(remoteFileUrl, tempDownloadFile)
             remoteFileChecksum = maven_repo_util.getSha1Checksum(tempDownloadFile)
             
             if (localFileChecksum != remoteFileChecksum):
                 logging.warning('Checksums do not match for artifact %s', relRepoPath)

             #logging.debug(maven_repo_util.getSha1Checksum(filepath))

def main():
    usage = "usage: %prog [options] REPOSITORY_PATH"
    cliOptParser = optparse.OptionParser(usage=usage, description='Compare a local Maven repository to a remote repository.')
    cliOptParser.add_option('-l', '--loglevel',
            default='info',
            help='Set the level of log output.  Can be set to debug, info, warning, error, or critical')
    cliOptParser.add_option('-u', '--url',
            default='http://repo1.maven.org/maven2/', 
            help='URL of the remote repository to use for comparison ')

    (args, opts) = cliOptParser.parse_args()

    if (len(sys.argv) < 2):
        logging.error('Local repository path must be specified\n')
        cliOptParser.print_help()
        sys.exit()

    localRepoPath = sys.argv[1]
        
    # Set the log level
    log_level = args.loglevel.lower()
    if (log_level == 'debug'):
        logging.basicConfig(level=logging.DEBUG) 
    if (log_level == 'info'):
        logging.basicConfig(level=logging.INFO) 
    elif (log_level == 'warning'):
        logging.basicConfig(level=logging.WARNING)
    elif (log_level == 'error'):
        logging.basicConfig(level=logging.ERROR)
    elif (log_level == 'critical'):
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning('Unrecognized log level: %s  Log level set to info', args.loglevel)


    # Read the list of dependencies
    if os.path.isfile(localRepoPath):
        logging.error('Local repository path is a file instead of a directory: %s', localRepoPath)
        sys.exit()
    elif not os.path.isdir(localRepoPath):
        logging.error('Local repository path must point to the root directory of a local maven repository: %s', localRepoPath)
        sys.exit()

    logging.info('Crawling repository located at: %s', localRepoPath)
    compareArtifacts(localRepoPath, args.url)


if  __name__ =='__main__':main()


