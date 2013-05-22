import urlparse
import urllib
import os

def urlExists(gavUrl):
    parsedUrl = urlparse.urlparse(gavUrl)
    protocol = parsedUrl[0]
    if protocol == 'http' or protocol == 'https':
        return urllib.urlopen(gavUrl).getcode() == 200
    else:
        if protocol == 'file':
            gavUrl = gavUrl[7:]
        return os.path.exists(gavUrl)

def slashAtTheEnd(url):
    if url.endswith('/'):
        return url
    else:
        return url + '/'

