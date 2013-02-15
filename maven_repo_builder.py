#! /usr/bin/env python

import argparse
import hashlib
import httplib
import os
import re
import shutil
import sys
import urllib2
import urlparse

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

    print('Downloading: ' + url)

    try:
        httpResponse = urllib2.urlopen(urllib2.Request(url))
        if (httpResponse.code == 200):
            fileName = fileName or getFileName(url, httpResponse)
            with open(fileName, 'wb') as localfile:
                shutil.copyfileobj(httpResponse,localfile)
        else:
            print('Unable to download, http code: ' + str(httpResponse.code))
        httpResponse.close()
    except urllib2.HTTPError as e:
        print('HTTPError = ' + str(e.code))
    except urllib2.URLError as e:
        print('URLError = ' + str(e.reason))
    except httplib.HTTPException as e:
        print('HTTPException')


def downloadArtifact(remoteRepoUrl, localRepoDir, artifact):
    """Download artifact from a remote repository along with pom and source jar"""
    artifactLocalDir = localRepoDir + '/' + artifact.getDirPath()
    if not os.path.exists(artifactLocalDir):
        os.makedirs(artifactLocalDir)

    # Download main artifact
    artifactUrl = remoteRepoUrl + '/' + artifact.getArtifactFilepath()
    artifactLocalPath = os.path.join(localRepoDir, artifact.getArtifactFilepath())
    if not os.path.exists(artifactLocalPath):
        download(artifactUrl, artifactLocalPath)
 
    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomUrl = remoteRepoUrl + '/' + artifact.getPomFilepath()
        artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
        if not os.path.exists(artifactPomLocalPath):
            download(artifactPomUrl, artifactPomLocalPath)
    
    # Download sources
    if artifact.getArtifactType() != 'pom':
        artifactSourcesUrl = remoteRepoUrl + '/' + artifact.getSourcesFilepath()
        artifactSourcesLocalPath = os.path.join(localRepoDir, artifact.getSourcesFilepath())
        if not os.path.exists(artifactSourcesLocalPath):
            download(artifactSourcesUrl, artifactSourcesLocalPath)


def copyArtifact(remoteRepoPath, localRepoDir, artifact):
    """Download artifact from a remote repository along with pom and source jar"""
    # Download main artifact
    artifactPath = os.path.join(remoteRepoPath, artifact.getArtifactFilepath())
    artifactLocalPath = os.path.join(localRepoDir, artifact.getArtifactFilepath())
    if os.path.exists(artifactPath) and not os.path.exists(artifactLocalPath):
        artifactLocalDir = os.path.join(localRepoDir, artifact.getDirPath())
        if not os.path.exists(artifactLocalDir):
            os.makedirs(artifactLocalDir)
        print('Copying file: ' + artifactPath)
        shutil.copyfile(artifactPath, artifactLocalPath)

    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomPath = os.path.join(remoteRepoPath, artifact.getPomFilepath())
        artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
        if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
            print('Copying file: ' + artifactPomPath)
            shutil.copyfile(artifactPomPath, artifactPomLocalPath)

    # Download sources
    if artifact.getArtifactType() != 'pom':
        artifactSourcesPath = os.path.join(remoteRepoPath, artifact.getSourcesFilepath())
        artifactSourcesLocalPath = os.path.join(localRepoDir, artifact.getSourcesFilepath())
        if os.path.exists(artifactSourcesPath) and not os.path.exists(artifactSourcesLocalPath):
            print('Copying file: ' + artifactSourcesPath)
            shutil.copyfile(artifactSourcesPath, artifactSourcesLocalPath)


def depListToArtifactList(depList):
    """Convert the maven GAV to a URL relative path"""
    regexComment = re.compile('#.*$')
    #regexLog = re.compile('^\[\w*\]')
    regexGAV = re.compile('(([\w\-.]+:){3}[\w\-.]+)(:[\w]*\S)?')
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
    if protocol == 'http' or protocol == 'https':
        for artifact in artifactList:
            downloadArtifact(remoteRepoUrl, localRepoDir, artifact)
    elif protocol == 'file':
        repoPath = remoteRepoUrl.replace('file://', '')
        for artifact in artifactList:
            copyArtifact(repoPath, localRepoDir, artifact)
    else:
        print('Unknown protocol: ' + protocol)


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
        print('Generate checksum: ' + sumfile)
        sum = sum_constr
        with open(mavenfile, 'rb') as fobj:
            while True:
                content = fobj.read(8192)
                if not content:
                    break
                sum.update(content)
        with open(sumfile, 'w') as sumobj:
            sumobj.write(sum.hexdigest() + '\n')


def main():    
    cliArgParser = argparse.ArgumentParser(description='Generate a Maven repository.')
    cliArgParser.add_argument('-u', '--url', 
            default='http://repository.jboss.org/nexus/content/groups/public/', 
            help='URL of the remote repository from which artifacts are downloaded')
    cliArgParser.add_argument('-d', '--directory', 
            default='local-repo', 
            help='Local file system directory of the new repository')
    cliArgParser.add_argument('-l', '--list', 
            default='dependency-list.txt', 
            help='The path to the file containing the list of dependencies to download')

    args = cliArgParser.parse_args()

    # Read the list of dependencies
    if os.path.isfile(args.list):
        depListFile = open(args.list)
        try:
            dependencyListLines = depListFile.readlines()
        except IOError as e:
            print('Unable to read file ' + args.dependencyList)
            print(e)
            sys.exit()
        finally:
            depListFile.close()
    else:
        print('Dependency List file does not exist')
        sys.exit()

    print('Reading artifact list...')
    artifacts = depListToArtifactList(dependencyListLines)
    print('Retrieving artifacts from repository: ' + args.url)
    retrieveArtifacts(args.url, args.directory, artifacts)
    print('Generating checksums...')
    generateChecksums(args.directory)
    print('Repository creation complete')


if  __name__ =='__main__':main()


