
"""maven_repo_util.py: Common functions for dealing with a maven repository"""

import hashlib
import httplib
import logging
import os
import shutil
import urllib
import urlparse
import re
from subprocess import Popen
from subprocess import PIPE
from xml.etree.ElementTree import ElementTree


# Constants
MAX_THREADS = 10


# Functions
def setLogLevel(level):
    """Sets the desired log level."""
    lLevel = level.lower()
    if (lLevel == 'debug'):
        logLevel = logging.DEBUG
    elif (lLevel == 'info'):
        logLevel = logging.INFO
    elif (lLevel == 'warning'):
        logLevel = logging.WARNING
    elif (lLevel == 'error'):
        logLevel = logging.ERROR
    elif (lLevel == 'critical'):
        logLevel = logging.CRITICAL
    else:
        logLevel = logging.INFO
        logging.warning('Unrecognized log level: %s  Log level set to info', level)
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logLevel)


def getSha1Checksum(filepath):
    return getChecksum(filepath, hashlib.sha1())


def getChecksum(filepath, sum_constr):
    """Generate a checksums for the file using the given algorithm"""
    logging.debug('Generate %s checksum for: %s', sum_constr.name.upper(), filepath)
    checksum = sum_constr
    with open(filepath, 'rb') as fobj:
        while True:
            content = fobj.read(8192)
            if not content:
                fobj.close()
                break
            checksum.update(content)
    return checksum.hexdigest()


def checkChecksum(filepath):
    """Checks if SHA1 and MD5 checksums equals to the ones saved in corresponding files if they are available."""
    assert os.path.exists(filepath)

    return _checkChecksum(filepath, hashlib.md5()) and _checkChecksum(filepath, hashlib.sha1())


def _checkChecksum(filepath, sum_constr):
    """Checks if desired checksum equals to the one saved in corresponding file if it is available."""
    checksumFilepath = filepath + '.' + sum_constr.name.lower()
    if os.path.exists(checksumFilepath):
        logging.debug("Checking %s checksum of %s", sum_constr.name.upper(), filepath)
        generatedChecksum = getChecksum(filepath, sum_constr)
        with open(checksumFilepath, "r") as checksumFile:
            downloadedChecksum = checksumFile.read()
        if generatedChecksum != downloadedChecksum:
            return False

        logging.debug("%s checksum of %s OK.", sum_constr.name.upper(), filepath)
    else:
        logging.debug("Checksum file %s doesn't exist, skipping the check.", checksumFilepath)

    return True


def str2bool(v):
    if v.lower() in ['true', 'yes', 't', 'y', '1']:
        return True
    elif v.lower() in ['false', 'no', 'f', 'n', '0']:
        return False
    else:
        raise ValueError("Failed to convert '" + v + "' to boolean")


def gavExists(repoUrl, artifact):
    """Checks if GAV of the given artifact exists in repository with the given root URL."""
    logging.debug("Checking if %s exists in repository %s", str(artifact), repoUrl)

    repoUrl = slashAtTheEnd(repoUrl)

    gavUrl = repoUrl + artifact.getDirPath()
    result = urlExists(gavUrl)

    if not result:
        logging.debug("URL %s does not exist, trying to find the version in artifact metadata", gavUrl)
        metadataUrl = repoUrl + artifact.getArtifactDirPath() + "maven-metadata.xml"
        gaPath = getTempDir(artifact.getArtifactDirPath())
        metadataFilePath = gaPath + 'maven-metadata.xml'
        if os.path.exists(metadataFilePath):
            fetched = True
        else:
            fetched = fetchFile(metadataUrl, gaPath)
        if fetched:
            metadataDoc = ElementTree(file=metadataFilePath)
            root = metadataDoc.getroot()
            for versionTag in root.findall("versioning/versions/version"):
                if versionTag.text == artifact.version:
                    result = True
                    break
        else:
            # we want to try pom file only when there are no metadata present
            pomUrl = repoUrl + artifact.getPomFilepath()
            logging.debug("URL %s does not exist. Trying pom file at %s", metadataUrl, pomUrl)
            result = urlExists(pomUrl)

    logging.debug("Artifact %s %sfound at %s", str(artifact), ("" if result else "not "), repoUrl)

    return result


def urlExists(url):
    parsedUrl = urlparse.urlparse(url)
    protocol = parsedUrl[0]
    if protocol == 'http' or protocol == 'https':
        if protocol == 'http':
            connection = httplib.HTTPConnection(parsedUrl[1])
        else:
            connection = httplib.HTTPSConnection(parsedUrl[1])
        connection.request('HEAD', parsedUrl[2])
        response = connection.getresponse()
        return response.status == 200
    else:
        if protocol == 'file':
            url = url[7:]
        return os.path.exists(url)


def urlProtocol(url):
    """Determines the protocol in the url, can be empty if there is none in the url."""
    parsedUrl = urlparse.urlparse(url)
    return parsedUrl[0]


def slashAtTheEnd(url):
    """
    Adds a slash at the end of given url if it is missing there.

    :param url: url to check and update
    :returns: updated url
    """
    if url.endswith('/'):
        return url
    else:
        return url + '/'


def transformAsterixStringToRegexp(string):
    return re.escape(string).replace("\\*", ".*")


def getRegExpsFromStrings(strings):
    rep = re.compile("^r\/.*\/$")
    regExps = []
    for s in strings:
        if rep.match(s):
            regExps.append(re.compile(s[2:-1]))
        else:
            regExps.append(re.compile(transformAsterixStringToRegexp(s)))
    return regExps


def printArtifactList(artifactList):
    for gat in artifactList:
        for priority in artifactList[gat]:
            for version in artifactList[gat][priority]:
                print artifactList[gat][priority][version] + "\t" + gat + ":" + version


def fetchFile(fileUrl, destDir):
    parsedUrl = urlparse.urlparse(fileUrl)
    protocol = parsedUrl[0]
    filename = fileUrl.split("/")[-1]
    filepath = destDir + '/' + filename

    if not os.path.isdir(destDir):
        os.makedirs(destDir)

    # Download only files that do not exist yet
    if filename and not os.path.isfile(filepath):
        logging.debug("Downloading file %s", fileUrl)
        if protocol == 'http' or protocol == 'https':
            try:
                (filename, headers) = urllib.URLopener().retrieve(fileUrl, filepath)
                return True
            except Exception as ex:
                logging.debug("Unable to retrieve %s: %s", fileUrl, str(ex))
                return False
        elif protocol == 'file':
            shutil.copy2(fileUrl.replace('file://', ''), destDir)
            return True
        else:
            logging.warning("File %s could not be downloaded, protocol %s is not supported",
                            fileUrl, protocol)


def getTempDir(relativePath=""):
    """Gets temporary directory for this running instance of Maven Repository Builder."""
    return '/tmp/maven-repo-builder/' + str(os.getpid()) + "/" + relativePath


def cleanTempDir():
    """Cleans temporary directory for this running instance of Maven Repository Builder."""
    if os.path.exists(getTempDir()):
        try:
            shutil.rmtree(getTempDir())
        except BaseException as ex:
            logging.error("An error occured while cleaning up temporary directory: %s", str(ex))


def updateSnapshotVersionSuffix(artifact, repoUrl):
    """
    Updates snapshotVersionSuffix in given artifact if the artifact is snapshot and pom
    file with '-SNAPSHOT' in filename does not exist. It reads maven-metadata.xml in
    artifact's directory and reads from there timastamp and builn number of the last
    snapshot build.
    """
    if not artifact.isSnapshot():
        return

    logging.debug("Adding snapshot version suffix for %s:%s:%s:%s", artifact.groupId,
                  artifact.artifactId, artifact.artifactType, artifact.version)
    pomUrl = slashAtTheEnd(repoUrl) + artifact.getPomFilepath()
    if urlExists(pomUrl):
        logging.debug("Not adding, because pom file %s exists", pomUrl)
        return

    metadataUrl = slashAtTheEnd(repoUrl) + artifact.getDirPath() + 'maven-metadata.xml'
    gavPath = getTempDir(artifact.getDirPath())
    metadataFilePath = gavPath + 'maven-metadata.xml'
    if not os.path.exists(metadataFilePath) and not fetchFile(metadataUrl, gavPath):
        logging.debug("Unable to read metadata from %s", metadataUrl)
        return

    metadataDoc = ElementTree(file=metadataFilePath)
    root = metadataDoc.getroot()
    timestamp = root.findtext("versioning/snapshot/timestamp")
    buildNumber = root.findtext("versioning/snapshot/buildNumber")

    if timestamp and buildNumber:
        artifact.snapshotVersionSuffix = '-' + timestamp + '-' + buildNumber
        logging.debug("Version suffix for %s:%s:%s:%s set to %s", artifact.groupId,
                      artifact.artifactId, artifact.artifactType, artifact.version,
                      artifact.snapshotVersionSuffix)


def somethingMatch(regexs, string):
    """
    Returns True if at least one of regular expresions from specified list matches string.

    :param regexs: list of regular expresions
    :param filename: string to match
    :returns: True if at least one of the regular expresions matched the string.
    """

    for regex in regexs:
        if regex.match(string):
            return True
    return False


def _sortVersionsWithAtlas(versions, versionSortedDir="versionSorter/"):
    """
    Returns sorted list of given verisons using Atlas versionSorter

    :param versions: versions to sort.
    :param versionSorterDir: directory with version sorter maven project
    :returns: sorted versions.
    """
    jarLocation = versionSortedDir + "target/versionSorter-1.0-SNAPSHOT.jar"
    if not os.path.isfile(jarLocation):
        logging.debug("Version sorter jar '%s' not found, running 'mvn clean package' in '%s'",
                      jarLocation,
                      versionSortedDir)
        Popen(["mvn", "clean", "package"], cwd=versionSortedDir).wait()
    args = ["java", "-jar", jarLocation] + versions
    ret = Popen(args, stdout=PIPE).communicate()[0].split('\n')[::-1]
    ret.remove("")
    return ret
