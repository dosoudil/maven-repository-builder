
"""maven_repo_util.py: Common functions for dealing with a maven repository"""

import hashlib
import httplib
import logging
import os
import shutil
import urllib2
import urlparse
import re


def download(url, filePath=None):
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
        httpResponse = urllib2.urlopen(urllib2.Request(url))
        if (httpResponse.code == 200):
            filePath = filePath or getFileName(url, httpResponse)
            with open(filePath, 'wb') as localfile:
                shutil.copyfileobj(httpResponse, localfile)
            logging.debug('Download complete')
        else:
            logging.warning('Unable to download, http code: %s', httpResponse.code)
        httpResponse.close()
        return httpResponse.code
    except urllib2.HTTPError as e:
        logging.debug('Unable to download, HTTP Response code = %s', e.code)
        return e.code
    except urllib2.URLError as e:
        logging.error('Unable to download, URLError: %s', e.reason)
    except httplib.HTTPException as e:
        logging.exception('Unable to download, HTTPException: %s', e.message)
    except ValueError as e:
        logging.error('ValueError: %s', e.message)


def getSha1Checksum(filepath):
    return getChecksum(filepath, hashlib.sha1())


def getChecksum(filepath, sum_constr):
    """Generate a checksums for the file using the given algorithm"""
    logging.debug('Generate %s checksum for: %s', sum_constr.name, filepath)
    checksum = sum_constr
    with open(filepath, 'rb') as fobj:
        while True:
            content = fobj.read(8192)
            if not content:
                fobj.close()
                break
            checksum.update(content)
    return checksum.hexdigest()


def str2bool(v):
    if v.lower() in ['true', 'yes', 't', 'y', '1']:
        return True
    elif v.lower() in ['false', 'no', 'f', 'n', '0']:
        return False
    else:
        raise ValueError("Failed to convert '" + v + "' to boolean")


def urlExists(url):
    protocol = urlProtocol(url)
    if protocol == 'http' or protocol == 'https':
        return urllib2.urlopen(url).getcode() == 200
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

