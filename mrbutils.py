import urlparse
import urllib
import os
import re


def urlExists(url):
    protocol = urlProtocol(url)
    if protocol == 'http' or protocol == 'https':
        return urllib.urlopen(url).getcode() == 200
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

