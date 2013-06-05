import logging
import mrbutils
from maven_artifact import MavenArtifact


class Filter:

    def __init__(self, config):
        self.config = config

    def filter(self, artifactList):
        logging.debug("Filter received %d GATs in the list.", len(artifactList))
        artifactList = self._filterExcludedGAVs(artifactList, self.config.excludedGAVs)
        artifactList = self._filterDuplicates(artifactList)
        artifactList = self._filterExcludedRepositories(artifactList,
                                                        self.config.excludedRepositories)
        return artifactList

    def _filterExcludedGAVs(self, artifactList, gavs):
        for gav in gavs:
            artifact = MavenArtifact.createFromGAV(gav)
            gaColon = artifact.getGA() + ":"
            for gat in artifactList.keys():
                if gat.startswith(gaColon):
                    for priority in artifactList[gat].keys():
                        if not artifact.version in artifactList[gat][priority]:
                            continue
                        del artifactList[gat][priority][artifact.version]
                        if not artifactList[gat][priority]:
                            del artifactList[gat][priority]
                    if not artifactList[gat]:
                        del artifactList[gat]
        return artifactList

    def _filterExcludedRepositories(self, artifactList, repositories):
        for gat in artifactList.keys():
            groupId = gat.split(':')[0]
            artifactId = gat.split(':')[1]
            artifactType = gat.split(':')[2]
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    artifact = MavenArtifact(groupId, artifactId, artifactType, version)
                    if _isArtifactInRepos(repositories, artifact):
                        del artifactList[gat][priority][version]
                if not artifactList[gat][priority]:
                    del artifactList[gat][priority]
            if not artifactList[gat]:
                del artifactList[gat]

        return artifactList

    def _filterDuplicates(self, artifactList):
        for gat in artifactList.keys():
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    for pr in artifactList[gat].keys():
                        if pr <= priority:
                            continue
                        if version in artifactList[gat][pr]:
                            del artifactList[gat][pr][version]
                if not artifactList[gat][priority]:
                    del artifactList[gat][priority]
            if not artifactList[gat]:
                del artifactList[gat]
        return artifactList


def _somethingMatch(regexs, filename):
    for regex in regexs:
        if regex.match(filename):
            return True
    return False


def _isArtifactInRepos(repositories, artifact):
    for repository in repositories:
        url = mrbutils.slashAtTheEnd(repository) + artifact.getDirPath()
        if mrbutils.urlExists(url):
            return True
    return False
