import urlparse
import os
from subprocess import Popen
from subprocess import PIPE


def buildList(configuration):
    artifactList = {}
    priority = 0
    for source in configuration.artifactSources:
        priority += 1

        if source['type'] == 'mead-tag':
            artifacts = listMeadTagArtifacts(source['koji-url'],source['download-root-url'],source['tag-name'])
        elif source['type'] == 'dependency-list':
            artifacts = listDependencies(source['git-url'],source['module'],source['repo-urls'])
        elif source['type'] == 'nexus-repository':
            artifacts = listNexusRepository(source['nexus-url'],source['repo-name'])
        elif source['type'] == 'local-repository':
            artifacts = listDirectoryArtifacts(source['root-dir'])
        elif source['type'] == 'artifacts':
            pass
        else:
            print "Unsupported source type:", source['type']

        for artifact in artifacts:
            ga = artifact.groupId + ':' + artifact.artifactId

            if not ga in artifactList:
                artifactList[ga] = {}
            if not priority in artifactList[ga]:
                artifactList[ga][priority] = {}

            artifactList[ga][priority][artifact.version] = getFiles(artifacts[artifact])
    return artifactList


def getFiles(gavUrl):
    parsedUrl = urlparse.urlparse(gavUrl)
    protocol = parsedUrl[0]
    if protocol == 'http' or protocol == 'https':
        return remoteFind(gavUrl)
    elif protocol == 'file':
        return localFind(gavUrl)
    else:
        print 'Unknown protocol:', protocol

def localFind(gavUrl):
    files = []
    gavPath = gavUrl.replace('file://', '')
    for dirname, dirnames, filenames in os.walk(gavPath):
        for filename in filenames:
            files.append('file://'+os.path.join(gavPath, dirname, filename))
    return files

def remoteFind(gavUrl):
    files = []
    (out,_) = Popen(r'lftp -c "set ssl:verify-certificate no ; open '+gavurl+' ; find "', stdout=PIPE, shell=True).communicate()
    for line in out.split('\n'):
        if line == '': continue
        files.append(gavUrl + line)
    return files

