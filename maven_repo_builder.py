#! /usr/bin/env python

import argparse
import hashlib
import urllib2
import urlparse
import shutil
import urlparse
import os
import re

from maven_artifact import MavenArtifact


def download(url, fileName=None):
    """Download the given url to a local file"""
    if os.path.exists(fileName):
        return
    
    def getFileName(url, openUrl):
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

    print 'Downloading: ' + url

    try:
        httpResponse = urllib2.urlopen(urllib2.Request(url))
        if (httpResponse.code == 200):
            fileName = fileName or getFileName(url, httpResponse)
            with open(fileName, 'wb') as localfile:
                shutil.copyfileobj(httpResponse,localfile)
        else:
            print 'Unable to download, http code: ' + str(httpResponse.code) 
        httpResponse.close()
    except urllib2.HTTPError, e:
        print 'HTTPError = ' + str(e.code)
    except urllib2.URLError, e:
        print 'URLError = ' + str(e.reason)
    except httplib.HTTPException, e:
        print 'HTTPException'


def downloadArtifact(remoteRepoUrl, localRepoDir, artifact):
    """Download artifact from a remote repository along with pom and source jar"""
    artifactRelativePath = artifact.getRelativePath()
    artifactLocalDir = localRepoDir + '/' + artifactRelativePath
    if not os.path.exists(artifactLocalDir):
        os.makedirs(artifactLocalDir)

    # Download main artifact
    artifactUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' + artifact.getArtifactFilename()
    artifactLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getArtifactFilename())
    if not os.path.exists(artifactLocalPath):
        download(artifactUrl, artifactLocalPath)
 
    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' +  artifact.getPomFilename()
        artifactPomLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getPomFilename())
        if not os.path.exists(artifactPomLocalPath):
            download(artifactPomUrl, artifactPomLocalPath)
    
    # Download sources
    artifactSourcesUrl = remoteRepoUrl + '/' + artifactRelativePath + '/' + artifact.getSourcesFilename()
    artifactSourcesLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getSourcesFilename())
    if not os.path.exists(artifactSourcesLocalPath):
        download(artifactSourcesUrl, artifactSourcesLocalPath)

def copyArtifact(remoteRepoPath, localRepoDir, artifact):
    """Download artifact from a remote repository along with pom and source jar"""
    artifactRelativePath = artifact.getRelativePath()
    artifactLocalDir = localRepoDir + '/' + artifactRelativePath
    if not os.path.exists(artifactLocalDir):
        os.makedirs(artifactLocalDir)

    # Download main artifact
    artifactPath = os.path.join(remoteRepoPath, artifactRelativePath, artifact.getArtifactFilename())
    artifactLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getArtifactFilename())
    if os.path.exists(artifactPath) and not os.path.exists(artifactLocalPath):
        print 'Copying file: ' + artifactPath
        shutil.copyfile(artifactPath, artifactLocalPath)

    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomPath = os.path.join(remoteRepoPath, artifactRelativePath, artifact.getPomFilename())
        artifactPomLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getPomFilename())
        if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
            print 'Copying file: ' + artifactPomPath
            shutil.copyfile(artifactPomPath, artifactPomLocalPath)

    # Download sources
    artifactSourcesPath = os.path.join(remoteRepoPath, artifactRelativePath, artifact.getSourcesFilename())
    artifactSourcesLocalPath = os.path.join(localRepoDir, artifactRelativePath, artifact.getSourcesFilename())
    if os.path.exists(artifactSourcesPath) and not os.path.exists(artifactSourcesLocalPath):
        print 'Copying file: ' + artifactSourcesPath
        shutil.copyfile(artifactSourcesPath, artifactSourcesLocalPath)


def depListToArtifactList(depList):
    """Convert the maven GAV to a URL relative path"""
    regexComment = re.compile('#.*$')
    #regexLog = re.compile('^\[\w*\]')
    regexGAV = re.compile('([\w\-.]*:){4}[\w]*\S')
    artifactList = []
    for nextLine in depList:
        nextLine = regexComment.sub('', nextLine)
        nextLine = nextLine.strip()
        gav = regexGAV.search(nextLine)
        if gav:
            artifactList.append(MavenArtifact(gav.group(0)))
    return artifactList
           

def retrieveArtifacts(remoteRepoUrl, localRepoDir, artifactList):
    """Create a Maven repository based on a remote repository url and a list of artifacts"""
    if not os.path.exists(localRepoDir):
        os.makedirs(localRepoDir)
    parsedUrl = urlparse.urlparse(remoteRepoUrl)
    protocol = parsedUrl[0]
    repoPath = parsedUrl[2]
    if protocol == 'http':
        for artifact in artifactList:
            downloadArtifact(remoteRepoUrl, localRepoDir, artifact)
    elif protocol == 'file':
        for artifact in artifactList:
            copyArtifact(repoPath, localRepoDir, artifact)
    else:
        print 'Unknown protocol: ' + protocol


def generateChecksums(localRepoDir):
    """Generate checksums for all maven artifacts in a repository"""
    for root, dirs, files in os.walk(localRepoDir):
        for filename in files:
            generateChecksum(os.path.join(root, filename))
    

def generateChecksum(mavenfile):
    """Generate md5 and sha1 checksums for a maven repository artifact"""
    if os.path.splitext(mavenfile)[1] in ('.md5', '.sha1'):
        return
    if not os.path.isfile(mavenfile):
        return
    for ext, sum_constr in (('.md5', hashlib.md5()), ('.sha1', hashlib.sha1())):
        sumfile = mavenfile + ext
        if os.path.exists(sumfile):
            continue
        print 'Generate checksum: ' + sumfile
        sum = sum_constr
        with open(mavenfile, 'r') as fobj:
            while True:
                content = fobj.read(8192)
                if not content:
                    break
                sum.update(content)
        #fobj.close()
        with open(sumfile, 'w') as sumobj:
        #sumobj = file('%s/%s' % (mavendir, sumfile), 'w')
            sumobj.write(sum.hexdigest())
        #sumobj.close()

    
####################
# Main execution ###
####################
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

print 'Reading artifact list...'
artifacts = depListToArtifactList(dependencyListLines)
print 'Retrieving artifacts...'
retrieveArtifacts(args.repoUrl, args.path, artifacts)
print 'Generating checksums...'
generateChecksums(args.path)
print 'Repository creation complete'


