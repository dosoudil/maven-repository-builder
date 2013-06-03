
"""maven_repo_util.py: Common functions for dealing with a maven repository"""

import hashlib
import httplib
import logging
import os
import shutil
import urllib2
import urlparse


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
                if filename: return filename
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
    sum = sum_constr
    with open(filepath, 'rb') as fobj:
        while True:
            content = fobj.read(8192)
            if not content:
                fobj.close()
                break
            sum.update(content)
    return sum.hexdigest()

