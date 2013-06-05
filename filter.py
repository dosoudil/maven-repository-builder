import logging
import mrbutils
from maven_artifact import MavenArtifact


class Filter:

    def __init__(self, config):
        self.config = config

    def filter(self, artifactList):
        """
        Filter artifactList removing excluded GAVs, duplicates and GAVs that exists in
        excluded repositories.

        :param artifactList: artifactList from ArtifactListBuilder.
        :returns: filtered artifactList.
        """

        logging.debug("Filter received %d GATs in the list.", len(artifactList))
        artifactList = self._filterExcludedGAVs(artifactList, self.config.excludedGAVs)
        artifactList = self._filterDuplicates(artifactList)
        artifactList = self._filterExcludedRepositories(artifactList,
                                                        self.config.excludedRepositories)
        return artifactList

    def _filterExcludedGAVs(self, artifactList, gavs):
        """
        Filter artifactList removing specified GAVs.

        :param artifactList: artifactList to be filtered.
        :param gavs: list of GAVs to be filtered out from the artifactList.
        :returns: artifactList without arifacts that matched specified GAVs.
        """

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
        """
        Filter artifactList removing artifacts existing in specified repositories.

        :param artifactList: artifactList to be filtered.
        :param repositories: list of repositories to be filtered out from the artifactList.
        :returns: artifactList without arifacts that exists in specified repositories.
        """

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
        """
        Filter artifactList removing duplicate artifacts.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without duplicate arifacts from lower priorities.
        """

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
    """
    Returns True if at least one of regular expresions from specified list matches filenam.

    :param regexs: list of regular expresions
    :param filename: filename to match
    :returns: True if at least one of the regular expresions matched the filename.
    """

    for regex in regexs:
        if regex.match(filename):
            return True
    return False


def _isArtifactInRepos(repositories, artifact):
    """
    Returns True if specified artifact exists in at least one repositori from specified list.

    :param repositories: list of repository urls
    :param artifact: searched MavenArtifact
    :returns: True if specified artifact exists in at least one of the repositories.
    """

    for repository in repositories:
        url = mrbutils.slashAtTheEnd(repository) + artifact.getDirPath()
        if mrbutils.urlExists(url):
            return True
    return False
