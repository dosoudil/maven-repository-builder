import urlparse
import urllib

def urlExists(gavUrl):
    parsedUrl = urlparse.urlparse(gavUrl)
    protocol = parsedUrl[0]
    if protocol == 'http' or protocol == 'https':
        return urllib.urlopen(gavUrl).getcode() == 200
    else:
        return os.path.exists(gavUrl)

def slashAtTheEnd(url):
    if url.endswith('/'):
        return url
    else:
        return url + '/'

