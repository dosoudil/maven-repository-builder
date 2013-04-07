#! /usr/bin/env python

import hashlib
import httplib
import logging
import optparse
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
                lambda x: x.strip().split('=') if '=' in x else (x.strip(), ''),
                openUrl.info()['Content-Disposition'].split(';')))
            if 'filename' in cd:
                filename = cd['filename'].strip("\"'")
                if filename: return filename
        # if no filename was found above, parse it out of the final URL.
        return os.path.basename(urlparse.urlsplit(openUrl.url)[2])

    logging.info('Downloading: %s', url)

    try:
        httpResponse = urllib2.urlopen(urllib2.Request(url))
        if (httpResponse.code == 200):
            fileName = fileName or getFileName(url, httpResponse)
            with open(fileName, 'wb') as localfile:
                shutil.copyfileobj(httpResponse, localfile)
        else:
            logging.error('Unable to download, http code: %s', httpResponse.code)
        httpResponse.close()
    except urllib2.HTTPError as e:
        logging.error('HTTPError = %s', e.code)
    except urllib2.URLError as e:
        logging.error('URLError = %s', e.reason)
    except httplib.HTTPException as e:
        logging.exception('HTTPException')


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
        logging.info('Copying file: ' + artifactPath)
        shutil.copyfile(artifactPath, artifactLocalPath)

    # Download pom
    if artifact.getArtifactFilename() != artifact.getPomFilename():
        artifactPomPath = os.path.join(remoteRepoPath, artifact.getPomFilepath())
        artifactPomLocalPath = os.path.join(localRepoDir, artifact.getPomFilepath())
        if os.path.exists(artifactPomPath) and not os.path.exists(artifactPomLocalPath):
            logging.info('Copying file: ' + artifactPomPath)
            shutil.copyfile(artifactPomPath, artifactPomLocalPath)

    # Download sources
    if artifact.getArtifactType() != 'pom':
        artifactSourcesPath = os.path.join(remoteRepoPath, artifact.getSourcesFilepath())
        artifactSourcesLocalPath = os.path.join(localRepoDir, artifact.getSourcesFilepath())
        if os.path.exists(artifactSourcesPath) and not os.path.exists(artifactSourcesLocalPath):
            logging.info('Copying file: ' + artifactSourcesPath)
            shutil.copyfile(artifactSourcesPath, artifactSourcesLocalPath)


def depListToArtifactList(depList):
    """Convert the maven GAV to a URL relative path"""
    regexComment = re.compile('#.*$')
    #regexLog = re.compile('^\[\w*\]')
    # Match pattern groupId:artifactId:type:[classifier:]version[:scope]
    regexGAV = re.compile('(([\w\-.]+:){3}([\w\-.]+:)?([\d][\w\-.]+))(:[\w]*\S)?')
    artifactList = []
    for nextLine in depList:
        nextLine = regexComment.sub('', nextLine)
        nextLine = nextLine.strip()
        gav = regexGAV.search(nextLine)
        if gav:
            artifactList.append(MavenArtifact(gav.group(1)))
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
        logging.error('Unknown protocol: %s', protocol)


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
        logging.info('Generate checksum: %s', sumfile)
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
    usage = "usage: %prog [-h] [-u URL] [-d DIRECTORY] [-l ARTIFACT_LIST]"
    cliOptParser = optparse.OptionParser(usage=usage, description='Generate a Maven repository.')
    cliOptParser.add_option('-d', '--debug',
            default='info',
            help='Set the level of log output.  Can be set to debug, info, warning, error, or critical')
    cliOptParser.add_option('-u', '--url',
            default='http://repo1.maven.org/maven2/', 
            help='URL of the remote repository from which artifacts are downloaded')
    cliOptParser.add_option('-o', '--output',
            default='local-maven-repository',
            help='Local output directory for the new repository')
    cliOptParser.add_option('-l', '--list',
            default='artifact-list.txt',
            help='The path to the file containing the list of artifacts to download')

    (args, opts) = cliOptParser.parse_args()

    # Set the log level
    log_level = args.debug.lower()
    if (log_level == 'debug'):
        logging.basicConfig(level=logging.DEBUG) 
    if (log_level == 'info'):
        logging.basicConfig(level=logging.INFO) 
    elif (log_level == 'warning'):
        logging.basicConfig(level=logging.WARNING)
    elif (log_level == 'error'):
        logging.basicConfig(level=logging.ERROR)
    elif (log_level == 'critical'):
        logging.basicConfig(level=logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning('Unrecognized log level: %s  Log level set to info', args.debug)

 
    # Read the list of dependencies
    if os.path.isfile(args.list):
        depListFile = open(args.list)
        try:
            dependencyListLines = depListFile.readlines()
        except IOError as e:
            logging.exception('Unable to read file %s', args.list)
            sys.exit()
        finally:
            depListFile.close()
    else:
        logging.error('File %s does not exist', args.list)
        sys.exit()

    logging.info('Reading artifact list...')
    artifacts = depListToArtifactList(dependencyListLines)
    logging.info('Retrieving artifacts from repository: %s', args.url)
    retrieveArtifacts(args.url, args.output, artifacts)
    logging.info('Generating checksums...')
    generateChecksums(args.output)
    logging.info('Repository created in directory: %s', args.output)


if  __name__ =='__main__':main()


