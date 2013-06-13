
"""maven_repo_util.py: Common functions for dealing with a maven repository"""

import hashlib
import httplib
import logging
import os
import urlparse
import re


def setLogLevel(level):
    """Sets the desired log level."""
    logLevel = level.lower()
    if (logLevel == 'debug'):
        logging.basicConfig(level=logging.DEBUG)
    elif (logLevel == 'info'):
        logging.basicConfig(level=logging.INFO)
    elif (logLevel == 'warning'):
        logging.basicConfig(level=logging.WARNING)
    elif (logLevel == 'error'):
        logging.basicConfig(level=logging.ERROR)
    elif (logLevel == 'critical'):
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning('Unrecognized log level: %s  Log level set to info', level)


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


def printArtifactList(artifactList):
    for gat in artifactList:
        for priority in artifactList[gat]:
            for version in artifactList[gat][priority]:
                print artifactList[gat][priority][version] + "\t" + gat + ":" + version
