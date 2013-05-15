#!/usr/bin/env python

import re
import koji
from maven_artifact import MavenArtifact


def listMeadTagArtifacts(kojiUrl, tagName):
    """Loads maven artifacts from koji (brew/mead).

    Returns list of MavenArtifact objects"""

    kojiSession = koji.ClientSession(kojiUrl)
    kojiArtifacts = kojiSession.getLatestMavenArchives(tagName)
    kojiArchiveTypes = kojiSession.getArchiveTypes()

    artifacts = []
    for artifact in kojiArtifacts:
        mavenArtifact = MavenArtifact(artifact['group_id'], artifact['artifact_id'],
                        _findArtifactType(artifact['type_id'], kojiArchiveTypes)['name'],
                        artifact['version'], _parseClassifier(artifact['filename']))

        artifacts.append(mavenArtifact)
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


def listRepository(srcRepoRoot):
    pass


def listDirectoryArtifacts(directoryPath):
    pass


def main():
    artifacts = listMeadTagArtifacts('http://brewhub.devel.redhat.com/brewhub',
                                     'brms-5.3.0')

    print '[%s]' % ', '.join(map(str, artifacts))


if __name__ == '__main__':
    main()
