#!/usr/bin/env python

"""
maven_repo_builder.py: Fetch artifacts into a location, where a Maven repository is being built given
a list of artifacts and a remote repository URL.
"""

import hashlib
import logging
import optparse
import os

import artifact_downloader
import artifact_list_generator
import maven_repo_util
from maven_repo_util import ChecksumMode


def generateChecksums(localRepoDir):
    """Generate checksums for all maven artifacts in a repository"""
    for root, dirs, files in os.walk(localRepoDir):
        for filename in files:
            generateChecksumFiles(os.path.join(root, filename))


def generateChecksumFiles(filepath):
    """Generate md5 and sha1 checksums for a maven repository artifact"""
    if os.path.splitext(filepath)[1] in ('.md5', '.sha1'):
        return
    if not os.path.isfile(filepath):
        return
    for ext, sum_constr in (('.md5', hashlib.md5()), ('.sha1', hashlib.sha1())):
        sumfile = filepath + ext
        if os.path.exists(sumfile):
            continue
        checksum = maven_repo_util.getChecksum(filepath, sum_constr)
        with open(sumfile, 'w') as sumobj:
            sumobj.write(checksum)


def main():
    usage = "Usage: %prog [-c CONFIG] [-a CLASSIFIERS] [-u URL] [-o OUTPUT_DIRECTORY] [FILE...]"
    description = ("Generate a Maven repository based on a file (or files) containing "
                   "a list of artifacts.  Each list file must contain a single artifact "
                   "per line in the format groupId:artifactId:fileType:<classifier>:version "
                   "The example artifact list contains more information. Another usage is "
                   "to provide Artifact List Generator configuration file. There is also "
                   "sample configuration file in examples.")

    cliOptParser = optparse.OptionParser(usage=usage, description=description)
    cliOptParser.add_option(
        '-c', '--config', dest='config',
        help='Configuration file to use for generation of an artifact list for the repository builder'
    )
    cliOptParser.add_option(
        '-u', '--url',
        default='http://repo1.maven.org/maven2/',
        help='Comma-separated list of URLs of the remote repositories from which artifacts '
             'are downloaded. It is used along with artifact list files when no config file '
             'is specified.'
    )
    cliOptParser.add_option(
        '-o', '--output',
        default='local-maven-repository/maven-repository',
        help='Local output directory for the new repository'
    )
    cliOptParser.add_option(
        '-a', '--classifiers',
        default='sources',
        help='Comma-separated list of additional classifiers to download. It is possible to use "__all__" to '
             'request all available classifiers (works only when artifact list is generated from config). There '
             'can be a type specified with each classifiers separated by colon, e.g. sources:jar. The old way '
             'of separation of classifiers by colon is deprecated'
    )
    cliOptParser.add_option(
        '-s', '--checksummode',
        default=ChecksumMode.generate,
        choices=(ChecksumMode.generate, ChecksumMode.download, ChecksumMode.check),
        help='Mode of dealing with MD5 and SHA1 checksums. Possible choices are:                                   '
             'generate - generate the checksums (default)                   '
             'download - download the checksums if available, if not, generate them                              '
             'check - check if downloaded and generated checksums are equal'
    )
    cliOptParser.add_option(
        '-x', '--excludedtypes',
        default='zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z',
        help='Colon-separated list of filetypes to exclude. Defaults to '
             'zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z.'
    )
    cliOptParser.add_option(
        '-w', '--whitelist',
        help='Name of a file containing GATCV patterns allowing usage of stars or regular expressions when enclosed '
             'in "r/pattern/". It can force inclusion of artifacts with excluded types.'
    )
    cliOptParser.add_option(
        '-l', '--loglevel',
        default='info',
        help='Set the level of log output.  Can be set to debug, info, warning, error, or critical'
    )
    cliOptParser.add_option(
        '-L', '--logfile',
        help='Set the file in which the log output should be written.'
    )

    (options, args) = cliOptParser.parse_args()

    # Set the log level
    maven_repo_util.setLogLevel(options.loglevel, options.logfile)

    # generate lists of artifacts from configuration and the fetch them each list from it's repo
    artifactList = artifact_list_generator.generateArtifactList(options, args)
    artifact_downloader.fetchArtifactLists(artifactList, options.output, options.checksummode)

    logging.info('Generating missing checksums...')
    generateChecksums(options.output)
    logging.info('Repository created in directory: %s', options.output)

    #cleanup
    maven_repo_util.cleanTempDir()


if __name__ == '__main__':
    main()
