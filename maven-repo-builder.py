#! /usr/bin/env python

import urllib2
import shutil
import urlparse
import os
import re

# Download the given url to a local file
def download(url, fileName=None):
    def getFileName(url,openUrl):
        if 'Content-Disposition' in openUrl.info():
            # If the response has Content-Disposition, try to get filename from it
            cd = dict(map(
                lambda x: x.strip().split('=') if '=' in x else (x.strip(),''),
                openUrl.info()['Content-Disposition'].split(';')))
            if 'filename' in cd:
                filename = cd['filename'].strip("\"'")
                if filename: return filename
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(urlparse.urlsplit(openUrl.url)[2])

    r = urllib2.urlopen(urllib2.Request(url))
    try:
        fileName = fileName or getFileName(url,r)
        with open(fileName, 'wb') as f:
            shutil.copyfileobj(r,f)
    finally:
        r.close()

# Convert the maven GAV to a URL relative path
def depListToArtifactList(depList):
    regexComment = re.compile('#.*')
    regexLog = re.compile('^\[\w*]')
    #regexGAV = re.compile('\S*:\S*:\S')
    artifactList = []
    for nextLine in depList:
        print nextLine 
        nextLine = regexComment.sub('', nextLine)
        nextLine = regexLog.sub('', nextLine)
        nextLine = nextLine.strip()
        print nextLine
        if nextLine:
            artifactList.append(gavStringToArtifact(nextLine))
    return artifactList
           
# Convert a colon separated GAV to relative path groupId:artifactId:type:version
def gavStringToArtifact(gav):
    artifact = {}
    gavParts = gav.split(':')
    artifact['groupId'] = gavParts[0]
    artifact['artifactId'] = gavParts[1]
    artifact['type'] = gavParts[2]
    artifact['version'] = gavParts[3]
    return artifact

def getArtifactRelativePath(artifact):
    relativePath = artifact['groupId'].replace('.', '/') + '/'
    relativePath += artifact['artifactId'] + '/'
    relativePath += artifact['version'] + '/' 
    return relativePath

def getArtifactFilename(artifact):
    filename = artifact['artifactId'] + '-' + artifact['version'] + '.' + artifact['type']
    return filename

def createRepository(remoteRepoUrl, localRepoDir, artifactList):
    if not os.path.exists(localRepoDir):
        os.makedirs(localRepoDir)
    for artifact in artifactList:
        artifactRelativePath = getArtifactRelativePath(artifact)
        artifactDir = localRepoDir + '/' + artifactRelativePath
        if not os.path.exists(artifactDir):
            os.makedirs(artifactDir)
        artifactFilePath = artifactRelativePath + '/' + getArtifactFilename(artifact)
        artifactUrl = remoteRepoUrl + '/' + artifactFilePath
        artifactLocalPath = localRepoDir + '/' + artifactFilePath
        print 'downloading: ' + artifactUrl
        download(artifactUrl, artifactLocalPath)

# Main execution
dependencyPaths = []
remoteRepoUrl = 'http://repository.jboss.org/nexus/content/groups/public/'
localRepoDir = 'local-repo'

# Read the list of dependencies
f = open("dependency-list.txt")
dependencyListLines = f.readlines()
artifacts = depListToArtifactList(dependencyListLines)
createRepository(remoteRepoUrl, localRepoDir, artifacts)

#download ("http://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.pom")


