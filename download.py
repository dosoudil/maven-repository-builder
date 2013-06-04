import os
import urllib
import urlparse
import shutil
import logging


def fetchArtifact(fileUrl, destDir):
    parsedUrl = urlparse.urlparse(fileUrl)
    protocol = parsedUrl[0]
    filename = fileUrl.split("/")[-1]
    filepath = destDir + '/' + filename

    if not os.path.isdir(destDir):
        os.makedirs(destDir)

    # Download only files that do not exist in the repo dir
    if filename and not os.path.isfile(filepath):
        logging.info("Downloading file %s", fileUrl)
        if protocol == 'http' or protocol == 'https':
            urllib.urlretrieve(fileUrl, filepath)
            return True
        elif protocol == 'file':
            shutil.copy2(fileUrl.replace('file://', ''), destDir)
            return True
        else:
            logging.warning("File %s could not be downloaded, protocol %s is not supported",
                            fileUrl, protocol)
