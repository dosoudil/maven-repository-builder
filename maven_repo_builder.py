#! /usr/bin/env python

import argparse
import urllib2
import shutil
import urlparse
import os
import re

from maven_artifact import MavenArtifact

def download(url, fileName=None):
    """Download the given url to a local file"""
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

def downloadArtifact(remoteRepoUrl, localRepoDir, artifact):
    """Download artifact from a remote repository along with"""
    artifactRelativePath = artifact.getRelativePath()
    artifactLocalDir = localRepoDir + '/' + artifactRelativePath
    if not os.path.exists(artifactLocalDir):
        os.makedirs(artifactLocalDir)

    # Download main artifact
    artifactUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' + artifact.getArtifactFilename()
    artifactLocalPath = localRepoDir + '/' + artifactRelativePath + '/' + artifact.getArtifactFilename()
    print 'downloading: ' + artifactUrl
    download(artifactUrl, artifactLocalPath)
 
    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' +  artifact.getPomFilename()
        artifactPomLocalPath = localRepoDir + '/' + artifactRelativePath + '/' +  artifact.getPomFilename()
        download(artifactPomUrl, artifactPomLocalPath)
    
    # Download sources
    artifactSourcesUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' + artifact.getSourcesFilename()
    artifactSourcesLocalPath = localRepoDir + '/' + artifactRelativePath + '/' + artifact.getSourcesFilename()
    download(artifactSourcesUrl, artifactSourcesLocalPath)


def depListToArtifactList(depList):
    """Convert the maven GAV to a URL relative path"""
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
            artifactList.append(MavenArtifact(nextLine))
    return artifactList
           
def createRepository(remoteRepoUrl, localRepoDir, artifactList):
    if not os.path.exists(localRepoDir):
        os.makedirs(localRepoDir)
    for artifact in artifactList:
        downloadArtifact(remoteRepoUrl, localRepoDir, artifact)

# Main execution
cliArgParser = argparse.ArgumentParser(description='Generate a Maven repository.')
cliArgParser.add_argument('-r', '--repoUrl', default='http://repository.jboss.org/nexus/content/groups/public/', \
                             help='URL of the remote repository')
cliArgParser.add_argument('-p', '--path', default='local-repo', \
                             help='Local file system path to the new repository')
cliArgParser.add_argument('-d', '--dependencyList', default='dependency-list.txt', \
                             help='Path to the dependency list config file')

args = cliArgParser.parse_args()

# Read the list of dependencies
if os.path.isfile(args.dependencyList):
    depListFile = open(args.dependencyList)
    try:
        dependencyListLines = depListFile.readlines()
    except IOError as e:
        print 'Unable to read file ' + args.dependencyList  
        print e
        sys.exit()
    finally:
        depListFile.close()
else:
    print 'Dependency List file does not exist'
    sys.exit()

artifacts = depListToArtifactList(dependencyListLines)
createRepository(args.repoUrl, args.path, artifacts)



