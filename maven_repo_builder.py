#!/usr/bin/env python

import re
import koji
import os
import urllib
import urlparse
from maven_artifact import MavenArtifact


def listMeadTagArtifacts(kojiUrl, downloadRootUrl, tagName):
    """Loads maven artifacts from koji (brew/mead).

    Returns list of MavenArtifact objects"""

    kojiSession = koji.ClientSession(kojiUrl)
    kojiArtifacts = kojiSession.getLatestMavenArchives(tagName)
    kojiArchiveTypes = kojiSession.getArchiveTypes()

    artifacts = {}
    for artifact in kojiArtifacts:
        mavenArtifact = MavenArtifact(artifact['group_id'], artifact['artifact_id'],
                        _findArtifactType(artifact['type_id'], kojiArchiveTypes)['name'],
                        artifact['version'], _parseClassifier(artifact['filename']))

        gavUrl = slashAtTheEnd(downloadRootUrl) + artifact['build_name'] + '/'\
                 + artifact['build_version'] + '/' + artifact['build_release']\
                 + '/maven/' +  artifact['group_id'].replace('.', '/') + '/'\
                 +  artifact['artifact_id'] + '/' +  artifact['version'] + '/'
        artifacts[mavenArtifact] = gavUrl
    return artifacts


def _findArtifactType(typeId, artifactTypes):
    """Finds artifactType in dictionary artifactTypes by typeId."""
    for artifactType in artifactTypes:
        if artifactType['id'] == typeId:
            return artifactType


def _parseClassifier(filename):
    """Parse artifact classifier from filename, returns None if
       no classifier were retrieved.
    """
    result = re.findall(r'-(\w+).\w+$', filename)
    if len(result) == 1:
        return result[0]
    else:
        return None


def listDependencies(scmUrl, moduleName, srcRepoRoot):
    pass


def listNexusRepository(nexusUrl, repoName):
    from xml.etree import ElementTree

    nexusBase = slashAtTheEnd(nexusUrl)
    repoUrl = nexusBase + 'content/repositories/' + repoName + '/'
    artifacts = {}
    for index in range(ord('a'), ord('z')):
        qUrl = nexusBase + "service/local/lucene/search?q=" + chr(index) + "*&repositoryId=" + repoName
        xmlResult = urllib.urlopen(qUrl).read()
        et = ElementTree.fromstring(xmlResult)
        data = et.find('data')
        for artifact in data.findall("artifact"):
            mavenArtifact = MavenArtifact(artifact.find('groupId').text, artifact.find('artifactId').text,
                            '', artifact.find('version').text)

            gavUrl = repoUrl + mavenArtifact.groupId.replace('.', '/') + '/'\
                    +  mavenArtifact.artifactId + '/' +  mavenArtifact.version + '/'
            artifacts[mavenArtifact] = gavUrl

    return artifacts


def listDirectoryArtifacts(directoryPath):
    artifacts = {}
    regexGAV = re.compile(r'(^.*)/([^/]*)/([^/]*$)')
    for dirname, dirnames, filenames in os.walk(directoryPath):
        if not dirnames:
            gavPath = dirname.replace(directoryPath,'')
            gav = regexGAV.search(gavPath)
            mavenArtifact = MavenArtifact(gav.group(1).replace('/','.'), gav.group(2),
                                          '', gav.group(3), '')
            artifacts[mavenArtifact] = 'file://' + dirname
    return artifacts

def listArtifacts(urls, gavs):
    artifacts = {}
    for gav in gavs:
        artifact = maven_artifact.createFromGAV(gav)
        for url in urls:
            gavUrl = url + artifact.getDirPath()
            if _gavExistsInUrl(gavUrl):
                artifacts[artifact] = gavUrl
                break
        if not artifact in artifacts:
            print 'artifact ' + artifact.__str__() + ' not found in any url!'

def _gavExistsInUrl(gavUrl):
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


def main():
    artifacts = listNexusRepository("https://repository-basic.engineering.redhat.com/nexus/",
                                    "scratch-release-soa-brms-6-build")

    print '[%s]' % ',\n'.join(map(str, artifacts))


if __name__ == '__main__':
    main()
