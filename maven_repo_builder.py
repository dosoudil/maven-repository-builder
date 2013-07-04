#!/usr/bin/env python

"""
maven_repo_builder.py: Fetch artifacts into a location, where a Maven repository is being built given
a list of artifacts and a remote repository URL.
"""

import hashlib
import httplib
import logging
import optparse
import os
import re
import shutil
import sys
import threading
import urllib2
import urlparse
import Queue

import artifact_list_generator
import maven_repo_util
from maven_artifact import MavenArtifact
from multiprocessing.pool import ThreadPool


class _ChecksumMode:
    generate = 'generate'
    download = 'download'
    check = 'check'


def download(url, checksumMode, filePath=None):
    """Download the given url to a local file"""
    logging.debug('Attempting download: %s', url)

    if filePath:
        if os.path.exists(filePath):
            logging.debug('Local file already exists, skipping: %s', filePath)
            return
        localdir = os.path.dirname(filePath)
        if not os.path.exists(localdir):
            os.makedirs(localdir)

    def getFileName(url, openUrl):
        if 'Content-Disposition' in openUrl.info():
            # If the response has Content-Disposition, try to get filename from it
            cd = dict(map(
                lambda x: x.strip().split('=') if '=' in x else (x.strip(), ''),
                openUrl.info()['Content-Disposition'].split(';')))
            if 'filename' in cd:
                filename = cd['filename'].strip("\"'")
                if filename:
                    return filename
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(urlparse.urlsplit(openUrl.url)[2])

    try:
        retries = 3
        checksumsOk = False
        while retries > 0 and not checksumsOk:
            try:
                httpResponse = urllib2.urlopen(urllib2.Request(url))
                if (httpResponse.code == 200):
                    filePath = filePath or getFileName(url, httpResponse)
                    with open(filePath, 'wb') as localfile:
                        shutil.copyfileobj(httpResponse, localfile)

                    if checksumMode in (_ChecksumMode.download, _ChecksumMode.check):
                        md5Retries = 3
                        md5Downloaded = False
                        while md5Retries > 0 and not md5Downloaded:
                            md5Retries -= 1
                            logging.debug('Downloading MD5 checksum from %s', url + ".md5")
                            csHttpResponse = urllib2.urlopen(urllib2.Request(url + ".md5"))
                            md5FilePath = filePath + ".md5"
                            with open(md5FilePath, 'wb') as localfile:
                                shutil.copyfileobj(csHttpResponse, localfile)
                            if (csHttpResponse.code != 200):
                                logging.warning('Unable to download MD5 checksum, http code: %s', csHttpResponse.code)
                            elif os.path.getsize(md5FilePath) != 32:
                                logging.warning('Downloaded MD5 checksum have %d bytes instead of 32 bytes',
                                                os.path.getsize(md5FilePath))
                            else:
                                md5Downloaded = True

                        sha1Retries = 3
                        sha1Downloaded = False
                        while sha1Retries > 0 and not sha1Downloaded:
                            sha1Retries -= 1
                            logging.debug('Downloading SHA1 checksum from %s', url + ".sha1")
                            csHttpResponse = urllib2.urlopen(urllib2.Request(url + ".sha1"))
                            sha1FilePath = filePath + ".sha1"
                            with open(sha1FilePath, 'wb') as localfile:
                                shutil.copyfileobj(csHttpResponse, localfile)
                            if (csHttpResponse.code != 200):
                                logging.warning('Unable to download SHA1 checksum, http code: %s', csHttpResponse.code)
                            elif os.path.getsize(sha1FilePath) != 40:
                                logging.warning('Downloaded SHA1 checksum have %d bytes instead of 40 bytes',
                                                os.path.getsize(sha1FilePath))
                            else:
                                sha1Downloaded = True

                        if not md5Downloaded or not sha1Downloaded:
                            logging.warning('No chance to download checksums to %s correctly.', filePath)

                    if checksumMode == _ChecksumMode.check:
                        if maven_repo_util.checkChecksum(filePath):
                            checksumsOk = True
                    else:
                        checksumsOk = True

                    if checksumsOk:
                        logging.debug('Download of %s complete', filePath)
                    elif retries > 1:
                        logging.warning('Checksum problem with %s, retrying download...', url)
                        retries -= 1
                    else:
                        logging.error('Checksum problem with %s. No chance to download the file correctly. Exiting',
                                      url)
                        # Raise exception instaed of sys.exit as this code is not running in the main thread
                        raise Exception("Exiting...")
                else:
                    logging.warning('Unable to download, http code: %s', httpResponse.code)
                httpResponse.close()
                return httpResponse.code
            except urllib2.HTTPError as e:
                if retries > 1:
                    if e.code / 100 == 5:
                        logging.debug('Unable to download, HTTP Response code = %s, trying again...', e.code)
                        retries -= 1
                    else:
                        logging.debug('Unable to download, HTTP Response code = %s.', e.code)
                        return e.code
                else:
                    logging.debug('Unable to download, HTTP Response code = %s, giving up...', e.code)
                    return e.code
    except urllib2.URLError as e:
        logging.error('Unable to download, URLError: %s', e.reason)
    except httplib.HTTPException as e:
        logging.exception('Unable to download, HTTPException: %s', e.message)
    except ValueError as e:
        logging.error('ValueError: %s', e.message)


def downloadFile(fileUrl, fileLocalPath, checksumMode):
    """Downloads file from the given URL to local path if the path does not exist yet."""
    if os.path.exists(fileLocalPath):
        logging.debug("Artifact already downloaded: %s", fileUrl)
    else:
        returnCode = download(fileUrl, checksumMode, fileLocalPath)
        if (returnCode == 404):
            logging.warning("Remote file not found: %s", fileUrl)
        elif (returnCode >= 400):
            logging.warning("Error code %d returned while downloading %s", returnCode, fileUrl)


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
        downloadFile(artifactUrl, artifactLocalPath, checksumMode)

        if not artifact.getClassifier():
            # Download pom if the main type is not pom
            if artifact.getArtifactFilename() != artifact.getPomFilename():
                artifactPomUrl = remoteRepoUrl + artifact.getPomFilepath()
                artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
                downloadFile(artifactPomUrl, artifactPomLocalPath, checksumMode)

                # Download additional classifiers (only for non-pom artifacts)
                for classifier in classifiers:
                    artifactClassifierUrl = remoteRepoUrl + artifact.getClassifierFilepath(classifier)
                    artifactClassifierLocalPath = os.path.join(localRepoDir, artifact.getClassifierFilepath(classifier))
                    downloadFile(artifactClassifierUrl, artifactClassifierLocalPath, checksumMode)
    except Exception as ex:
        logging.error("Error while downloading artifact %s: %s", artifact, str(ex))
        errors.put(ex)


def copyFile(filePath, fileLocalPath, checksumMode):
    """Copies file from the given path to local path if the path does not exist yet."""
    if os.path.exists(fileLocalPath):
        logging.debug("Artifact already copy: " + filePath)
    else:
        if os.path.exists(filePath):
            shutil.copyfile(filePath, fileLocalPath)
            if checksumMode in (_ChecksumMode.download, _ChecksumMode.check):
                if os.path.exists(filePath + ".md5"):
                    shutil.copyfile(filePath + ".md5", fileLocalPath + ".md5")
                if os.path.exists(filePath + ".sha1"):
                    shutil.copyfile(filePath + ".sha1", fileLocalPath + ".sha1")

            if checksumMode == _ChecksumMode.check:
                if not maven_repo_util.checkChecksum(filePath):
                    logging.error('Checksum problem with copy of %s. Exiting', filePath)
                    sys.exit(1)
        else:
            logging.warning("Source file not found: %s", filePath)


def copyArtifact(remoteRepoPath, localRepoDir, artifact, classifiers, checksumMode):
    """Copy artifact from a repository on the local file system along with pom and source jar"""
    # Copy main artifact
    artifactPath = os.path.join(remoteRepoPath, artifact.getArtifactFilepath())
    artifactLocalPath = os.path.join(localRepoDir, artifact.getArtifactFilepath())
    if os.path.exists(artifactPath) and not os.path.exists(artifactLocalPath):
        artifactLocalDir = os.path.join(localRepoDir, artifact.getDirPath())
        if not os.path.exists(artifactLocalDir):
            os.makedirs(artifactLocalDir)
        logging.info('Copying file: %s', artifactPath)
        copyFile(artifactPath, artifactLocalPath, checksumMode)

    if not artifact.getClassifier():
        # Copy pom if the main type is not pom
        if artifact.getArtifactFilename() != artifact.getPomFilename():
            artifactPomPath = os.path.join(remoteRepoPath, artifact.getPomFilepath())
            artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
            if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
                logging.info('Copying file: %s', artifactPomPath)
                copyFile(artifactPomPath, artifactPomLocalPath, checksumMode)

            # Copy additional classifiers (only for non-pom artifacts)
            for classifier in classifiers:
                artifactClassifierPath = os.path.join(remoteRepoPath, artifact.getClassifierFilepath(classifier))
                artifactClassifierLocalPath = os.path.join(localRepoDir, artifact.getClassifierFilepath(classifier))
                if os.path.exists(artifactClassifierPath) and not os.path.exists(artifactClassifierLocalPath):
                    logging.info('Copying file: %s', artifactClassifierPath)
                    copyFile(artifactClassifierPath, artifactClassifierLocalPath, checksumMode)


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
            sys.exit(1)

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
            sumobj.write(checksum + '\n')


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
    cliOptParser.add_option('-c', '--config', dest='config',
            help='Configuration file to use for generation of an artifact list for the repository builder')
    cliOptParser.add_option('-u', '--url',
            default='http://repo1.maven.org/maven2/',
            help='URL of the remote repository from which artifacts are downloaded. It is used along with '
                 'artifact list files when no config file is specified.')
    cliOptParser.add_option('-o', '--output',
            default='local-maven-repository',
            help='Local output directory for the new repository')
    cliOptParser.add_option('-a', '--classifiers',
            default='sources',
            help='Colon-separated list of additional classifiers to download. It is possible to use "__all__" to '
                 'request all available classifiers (works only when artifact list is generated from config).')
    cliOptParser.add_option('-s', '--checksummode',
            default=_ChecksumMode.generate,
            choices=(_ChecksumMode.generate, _ChecksumMode.download, _ChecksumMode.check),
            help='Mode of dealing with MD5 and SHA1 checksums. Possible choices are:                                   '
                 'generate - generate the checksums (default)                   '
                 'download - download the checksums if available, if not, generate them                              '
                 'check - check if downloaded and generated checksums are equal')
    cliOptParser.add_option('-x', '--excludedtypes',
            default='zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z',
            help='Colon-separated list of filetypes to exclude. Defaults to '
                 'zip:ear:war:tar:gz:tar.gz:bz2:tar.bz2:7z:tar.7z.')
    cliOptParser.add_option('-l', '--loglevel',
            default='info',
            help='Set the level of log output.  Can be set to debug, info, warning, error, or critical')
    cliOptParser.add_option('-L', '--logfile',
            help='Set the file in which the log output should be written.')

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


if  __name__ == '__main__':
    main()
