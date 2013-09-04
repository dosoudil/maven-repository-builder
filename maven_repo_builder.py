#!/usr/bin/env python

"""
maven_repo_builder.py: Fetch artifacts into a location, where a Maven repository is being built given
a list of artifacts and a remote repository URL.
"""

import hashlib
import logging
import optparse
import os
import re
import sys
import threading
import urlparse
import Queue
from multiprocessing.pool import ThreadPool

import artifact_list_generator
import maven_repo_util
from maven_repo_util import ChecksumMode
from maven_artifact import MavenArtifact


def downloadArtifacts(remoteRepoUrl, localRepoDir, artifact, classifiers, checksumMode, mkdirLock, errors):
    """Download artifact from a remote repository along with pom and additional classifiers' jar"""
    logging.debug("Starting download of %s", str(artifact))

    artifactLocalDir = localRepoDir + '/' + artifact.getDirPath()

    try:
        # handle parallelism, when two threads checks if a directory exists and then both tries to create it
        mkdirLock.acquire()
        if not os.path.exists(artifactLocalDir):
            os.makedirs(artifactLocalDir)
        mkdirLock.release()

        remoteRepoUrl = maven_repo_util.slashAtTheEnd(remoteRepoUrl)

        # Download main artifact
        artifactUrl = remoteRepoUrl + artifact.getArtifactFilepath()
        artifactLocalPath = os.path.join(localRepoDir, artifact.getArtifactFilepath())
        maven_repo_util.fetchFile(artifactUrl, artifactLocalPath, checksumMode, exitOnError=True)

        if not artifact.getClassifier():
            # Download pom if the main type is not pom
            if artifact.getArtifactFilename() != artifact.getPomFilename():
                artifactPomUrl = remoteRepoUrl + artifact.getPomFilepath()
                artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
                maven_repo_util.fetchFile(artifactPomUrl, artifactPomLocalPath, checksumMode, exitOnError=True)

                # Download additional classifiers (only for non-pom artifacts)
                for classifier in classifiers:
                    artifactClassifierUrl = remoteRepoUrl + artifact.getClassifierFilepath(classifier)
                    if maven_repo_util.urlExists(artifactClassifierUrl):
                        artifactClassifierLocalPath = os.path.join(
                            localRepoDir, artifact.getClassifierFilepath(classifier))
                        maven_repo_util.fetchFile(
                            artifactClassifierUrl, artifactClassifierLocalPath, checksumMode, exitOnError=True)
    except BaseException as ex:
        logging.error("Error while downloading artifact %s: %s", artifact, str(ex))
        errors.put(ex)


def copyArtifact(remoteRepoPath, localRepoDir, artifact, classifiers, checksumMode):
    """Copy artifact from a repository on the local file system along with pom and source jar"""
    # Copy main artifact
    artifactPath = os.path.join(remoteRepoPath, artifact.getArtifactFilepath())
    artifactLocalPath = os.path.join(localRepoDir, artifact.getArtifactFilepath())
    if os.path.exists(artifactPath) and not os.path.exists(artifactLocalPath):
        maven_repo_util.fetchFile(artifactPath, artifactLocalPath, checksumMode)

    if not artifact.getClassifier():
        # Copy pom if the main type is not pom
        if artifact.getArtifactFilename() != artifact.getPomFilename():
            artifactPomPath = os.path.join(remoteRepoPath, artifact.getPomFilepath())
            artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
            if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
                maven_repo_util.fetchFile(artifactPomPath, artifactPomLocalPath, checksumMode)

            # Copy additional classifiers (only for non-pom artifacts)
            for classifier in classifiers:
                artifactClassifierPath = os.path.join(remoteRepoPath, artifact.getClassifierFilepath(classifier))
                artifactClassifierLocalPath = os.path.join(localRepoDir, artifact.getClassifierFilepath(classifier))
                if os.path.exists(artifactClassifierPath) and not os.path.exists(artifactClassifierLocalPath):
                    maven_repo_util.fetchFile(artifactClassifierPath, artifactClassifierLocalPath, checksumMode)


def depListToArtifactList(depList):
    """Convert the maven GAV to a URL relative path"""
    regexComment = re.compile('#.*$')
    #regexLog = re.compile('^\[\w*\]')
    # Match pattern groupId:artifactId:type:[classifier:]version[:scope]
    regexGAV = re.compile('(([\w\-.]+:){3}([\w\-.]+:)?([\d][\w\-.]+))(:[\w]*\S)?')
    artifactList = []
    for nextLine in depList:
        nextLine = regexComment.sub('', nextLine)
        nextLine = nextLine.strip()
        gav = regexGAV.search(nextLine)
        if gav:
            artifactList.append(MavenArtifact.createFromGAV(gav.group(1)))
    return artifactList


def fetchArtifacts(remoteRepoUrl, localRepoDir, artifactList, classifiers, excludedTypes, checksumMode):
    """Create a Maven repository based on a remote repository url and a list of artifacts"""
    logging.info('Retrieving artifacts from repository: %s', remoteRepoUrl)
    if not os.path.exists(localRepoDir):
        os.makedirs(localRepoDir)
    parsedUrl = urlparse.urlparse(remoteRepoUrl)
    protocol = parsedUrl[0]
    repoPath = parsedUrl[2]

    if protocol == 'http' or protocol == 'https':
        # Create thread pool
        pool = ThreadPool(maven_repo_util.MAX_THREADS)
        errors = Queue.Queue()
        mkdirLock = threading.Lock()

        for artifact in artifactList:
            if artifact.artifactType in excludedTypes:
                logging.info("Skipping download of %s:%s:%s:%s because of excluded type", artifact.groupId,
                             artifact.artifactId, artifact.artifactType, artifact.version)
                continue
            if artifact.isSnapshot():
                maven_repo_util.updateSnapshotVersionSuffix(artifact, remoteRepoUrl)
            pool.apply_async(
                downloadArtifacts,
                [remoteRepoUrl, localRepoDir, artifact, classifiers, checksumMode, mkdirLock, errors]
            )

        # Close pool and wait till all workers are finnished
        pool.close()
        pool.join()

        # If one of the workers threw error, exit with 1
        if not errors.empty():
            logging.error("During fetching files from repository %s %i error(s) occured.", remoteRepoUrl,
                          len(errors))

    elif protocol == 'file':
        repoPath = remoteRepoUrl.replace('file://', '')
        for artifact in artifactList:
            if artifact.artifactType in excludedTypes:
                logging.info("Skipping copy of %s:%s:%s:%s because of excluded type", artifact.groupId,
                             artifact.artifactId, artifact.artifactType, artifact.version)
                continue
            if artifact.isSnapshot():
                maven_repo_util.updateSnapshotVersionSuffix(artifact, remoteRepoUrl)
            copyArtifact(repoPath, localRepoDir, artifact, classifiers, checksumMode)
    else:
        logging.error('Unknown protocol: %s', protocol)


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

    # TODO: pkocandr - use argparse instead of optparse, which is deprecated since python 2.7
    cliOptParser = optparse.OptionParser(usage=usage, description=description)
    cliOptParser.add_option(
        '-c', '--config', dest='config',
        help='Configuration file to use for generation of an artifact list for the repository builder'
    )
    cliOptParser.add_option(
        '-u', '--url',
        default='http://repo1.maven.org/maven2/',
        help='URL of the remote repository from which artifacts are downloaded. '
             'It is used along with artifact list files when no config file is specified.'
    )
    cliOptParser.add_option(
        '-o', '--output',
        default='local-maven-repository',
        help='Local output directory for the new repository'
    )
    cliOptParser.add_option(
        '-a', '--classifiers',
        default='sources',
        help='Colon-separated list of additional classifiers to download. It is '
             'possible to use "__all__" to request all available classifiers '
             '(works only when artifact list is generated from config).'
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

    if not options.classifiers or options.classifiers == '__all__':
        classifiers = []
    else:
        classifiers = options.classifiers.split(":")

    if not options.excludedtypes:
        excludedtypes = []
    else:
        excludedtypes = options.excludedtypes.split(":")

    if options.config is None:
        if len(args) < 1:
            logging.error('Missing required command line argument: path to artifact list file')
            sys.exit(usage)

        # Read the list(s) of dependencies from the specified files
        artifacts = []
        for filename in args:
            if not os.path.isfile(filename):
                logging.warning('Dependency list file does not exist, skipping: %s', filename)
                continue

            logging.info('Reading artifact list from file: %s', filename)
            depListFile = open(filename)
            try:
                dependencyListLines = depListFile.readlines()
                artifacts.extend(depListToArtifactList(dependencyListLines))
            except IOError as e:
                logging.exception('Unable to read file %s: %s', filename, str(e))
                sys.exit(1)
            finally:
                depListFile.close()

        fetchArtifacts(options.url, options.output, artifacts, classifiers, excludedtypes, options.checksummode)
    else:
        # generate lists of artifacts from configuration and the fetch them each list from it's repo
        artifactList = artifact_list_generator.generateArtifactList(options)
        for repoUrl in artifactList.keys():
            artifacts = artifactList[repoUrl]
            fetchArtifacts(repoUrl, options.output, artifacts, classifiers, excludedtypes, options.checksummode)

    logging.info('Generating missing checksums...')
    generateChecksums(options.output)
    logging.info('Repository created in directory: %s', options.output)

    #cleanup
    maven_repo_util.cleanTempDir()


if __name__ == '__main__':
    main()
