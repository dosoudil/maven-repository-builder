#!/usr/bin/env python

"""
maven_repo_builder.py: Fetch artifacts into a location, where a Maven repository is being built given
a list of artifacts and a remote repository URL.
"""

import hashlib
import logging
import os
import re
import sys
import threading
import urlparse
import Queue
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from multiprocessing.pool import ThreadPool

import artifact_list_generator
import maven_repo_util
from maven_repo_util import ChecksumMode
from maven_artifact import MavenArtifact


def downloadArtifacts(remoteRepoUrl, localRepoDir, artifact, classifiers, checksumMode, mkdirLock, filesetLock,
                      fileset, errors):
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
        maven_repo_util.fetchFile(artifactUrl, artifactLocalPath, checksumMode, True, True, filesetLock, fileset)

        # Download pom if the main type is not pom
        if artifact.getArtifactFilename() != artifact.getPomFilename():
            artifactPomUrl = remoteRepoUrl + artifact.getPomFilepath()
            artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
            maven_repo_util.fetchFile(artifactPomUrl, artifactPomLocalPath, checksumMode, True, True, filesetLock,
                                      fileset)

            # Download additional classifiers (only for non-pom artifacts)
            for ct in classifiers:
                classifier = ct["classifier"]
                if "type" in ct:
                    artifactType = ct["type"]
                    classifierFilepath = artifact.getClassifierFilepath(classifier, artifactType)
                else:
                    classifierFilepath = artifact.getClassifierFilepath(classifier)
                artifactClassifierUrl = remoteRepoUrl + classifierFilepath
                if maven_repo_util.urlExists(artifactClassifierUrl):
                    artifactClassifierLocalPath = os.path.join(localRepoDir, classifierFilepath)
                    maven_repo_util.fetchFile(artifactClassifierUrl, artifactClassifierLocalPath, checksumMode,
                                              True, True, filesetLock, fileset)
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

    # Copy pom if the main type is not pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomPath = os.path.join(remoteRepoPath, artifact.getPomFilepath())
        artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
        if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
            maven_repo_util.fetchFile(artifactPomPath, artifactPomLocalPath, checksumMode)

        # Copy additional classifiers (only for non-pom artifacts)
        for ct in classifiers:
            classifier = ct["classifier"]
            if "type" in ct:
                artifactType = ct["type"]
                classifierFilepath = artifact.getClassifierFilepath(classifier, artifactType)
            else:
                classifierFilepath = artifact.getClassifierFilepath(classifier)
            artifactClassifierPath = os.path.join(remoteRepoPath, classifierFilepath)
            artifactClassifierLocalPath = os.path.join(localRepoDir, classifierFilepath)
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


def fetchArtifacts(remoteRepoUrl, localRepoDir, artifactList, classifiers, excludedTypes, whitelistedGATCVs,
                   checksumMode):
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
        filesetLock = threading.Lock()
        fileset = set([])

        for artifact in artifactList:
            if artifact.artifactType in excludedTypes:
                if maven_repo_util.somethingMatch(whitelistedGATCVs, artifact.getGATCV()):
                    logging.debug("Artifact %s not skipped, because its GATCV matches one of the whitelist patterns.",
                                  artifact.getGATCV())
                else:
                    logging.info("Skipping download of %s because of excluded type", artifact.getGATCV())
                    continue
            if artifact.isSnapshot():
                maven_repo_util.updateSnapshotVersionSuffix(artifact, remoteRepoUrl)
            pool.apply_async(
                downloadArtifacts,
                [remoteRepoUrl, localRepoDir, artifact, classifiers, checksumMode, mkdirLock, filesetLock, fileset,
                    errors]
            )

        # Close pool and wait till all workers are finnished
        pool.close()
        pool.join()

        # If one of the workers threw an error, log it
        if not errors.empty():
            logging.error("During fetching files from repository %s %i error(s) occured.", remoteRepoUrl,
                          errors.qsize())

    elif protocol == 'file':
        repoPath = remoteRepoUrl.replace('file://', '')
        for artifact in artifactList:
            if artifact.artifactType in excludedTypes:
                if maven_repo_util.somethingMatch(whitelistedGATCVs, artifact.getGATCV()):
                    logging.debug("Artifact %s not skipped, because its GATCV matches one of the whitelist patterns.",
                                  artifact.getGATCV())
                else:
                    logging.info("Skipping copy of %s because of excluded type", artifact.getGATCV())
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


def parseClassifiers(classifiersString):
    """
    Parses classifiers and types from command-line argument value. The result  is list of dictionaries. Each dictionary
    contains classifier value under "classifier" key and optionally type under "type" key. If no type is specified, then
    the key "type" is missing in the dictionary

    :param classifiersString: comma-separated list of classifiers with an optional prepended type separated by colon,
                              if no type specified, then the default type ("jar") is used
    :returns: list of dictionaries with structure e.g. {"classifiers": "sources", "type": "jar"}
    """
    if not classifiersString or classifiersString == '__all__':
        result = []
    else:
        classifiers = classifiersString.split(",")
        if len(classifiers) == 1 and classifiers.count(":") > 1:
            result = classifiersString.split(":")
        else:
            result = []
            for classifier in classifiers:
                colonCount = classifier.count(":")
                if colonCount == 0:
                    result.append({"classifier": classifier})
                elif colonCount == 1:
                    parts = classifier.split(":")
                    result.append({"classifier": parts[1], "type": parts[0]})
                else:
                    raise ValueError("Requested classifier value %s contains more than one colon." % classifier)

    return result


def main():
    description = (
        'Generate a Maven repository based on a file (or files) containing a list of\n'
        'artifacts.  Each list file must contain a single artifact per line in the\n'
        'format groupId:artifactId:fileType:<classifier>:version. The example artifact\n'
        'list contains more information. Another usage is to provide Artifact List\n'
        'Generator configuration file. There is also sample configuration file in\n'
        'examples.')

    cliOptParser = ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
    cliOptParser.add_argument(
        "artifact_list",
        nargs='*',
        help='File (or files) containing a list of artifacts. Used\n'
             'when no artifact list generator configuration is\n'
             'passed.'
    )
    cliOptParser.add_argument(
        '-c', '--config', dest='config',
        help='Configuration file to use for generation of an\n'
             'artifact list for the repository builder.'
    )
    cliOptParser.add_argument(
        '-u', '--url',
        default='http://repo1.maven.org/maven2/',
        help='URL of the remote repository from which artifacts are\n'
             'downloaded. It is used along with artifact list files\n'
             'when no config file is specified.'
    )
    cliOptParser.add_argument(
        '-o', '--output',
        default='local-maven-repository',
        help='Local output directory for the new repository.'
    )
    cliOptParser.add_argument(
        '-a', '--classifiers',
        default='sources',
        help='Comma-separated list of additional classifiers to\n'
             'download. It is possible to use "__all__" to request\n'
             'all available classifiers (works only when artifact\n'
             'list is generated from config). There can be a type\n'
             'specified with each classifiers separated by colon,\n'
             'e.g. sources:jar. The old way of separation of\n'
             'classifiers by colon is deprecated.'
    )
    cliOptParser.add_argument(
        '-s', '--checksummode',
        default=ChecksumMode.generate,
        choices=(ChecksumMode.generate, ChecksumMode.download, ChecksumMode.check),
        help='Mode of dealing with MD5 and SHA1 checksums. Possible\n'
             'choices are:\n'
             '  generate - generate the checksums (default)\n'
             '  download - download the checksums if available, if\n'
             '             not, generate them\n'
             '  check    - check if downloaded and generated\n'
             '             checksums are equal'
    )
    cliOptParser.add_argument(
        '-x', '--excludedtypes',
        default='zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z',
        help='Colon-separated list of filetypes to exclude. Defaults\n'
             'to zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z.'
    )
    cliOptParser.add_argument(
        '-w', '--whitelist',
        help='Name of a file containing GATCV patterns allowing\n'
             'usage of stars or regular expressions when enclosed in\n'
             '"r/pattern/". It can force inclusion of artifacts with\n'
             'excluded types.'
    )
    cliOptParser.add_argument(
        '-l', '--loglevel',
        default='info',
        help='Set the level of log output. Can be set to debug,\n'
             'info, warning, error, or critical.'
    )
    cliOptParser.add_argument(
        '-L', '--logfile',
        help='Set the file in which the log output should be\n'
             'written.'
    )

    args = cliOptParser.parse_args()

    # Set the log level
    maven_repo_util.setLogLevel(args.loglevel, args.logfile)

    classifiers = parseClassifiers(args.classifiers)

    if args.excludedtypes:
        excludedtypes = args.excludedtypes.split(":")
    else:
        excludedtypes = []

    if args.whitelist:
        lineList = maven_repo_util.loadFlatFile(args.whitelist)
        whitelistedGATCVs = maven_repo_util.getRegExpsFromStrings(lineList)
    else:
        whitelistedGATCVs = []

    if args.config is None:
        if len(args.artifact_list) < 1:
            logging.error('Missing required command line argument: path to artifact list file')
            sys.exit(cliOptParser.format_usage())

        # Read the list(s) of dependencies from the specified files
        artifacts = []
        for filename in args.artifact_list:
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

        fetchArtifacts(args.url, args.output, artifacts, classifiers, excludedtypes, whitelistedGATCVs,
                       args.checksummode)
    else:
        # generate lists of artifacts from configuration and the fetch them each list from it's repo
        artifactList = artifact_list_generator.generateArtifactList(args)
        for repoUrl in artifactList.keys():
            artifacts = artifactList[repoUrl]
            fetchArtifacts(repoUrl, args.output, artifacts, classifiers, excludedtypes, whitelistedGATCVs,
                           args.checksummode)

    logging.info('Generating missing checksums...')
    generateChecksums(args.output)
    logging.info('Repository created in directory: %s', args.output)

    #cleanup
    maven_repo_util.cleanTempDir()


if __name__ == '__main__':
    main()
