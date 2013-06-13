import logging
import maven_repo_util
import os
import re
from subprocess import Popen
from subprocess import PIPE
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

        artifactList = self._filterExcludedGAVs(artifactList)
        artifactList = self._filterDuplicates(artifactList)
        if self.config.singleVersion:
            artifactList = self._filterMultipleVersions(artifactList)
        artifactList = self._filterExcludedRepositories(artifactList)
        return artifactList

    def _filterExcludedGAVs(self, artifactList):
        """
        Filter artifactList removing specified GAVs.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without arifacts that matched specified GAVs.
        """

        regExps = _getRegExpsFromStrings(self.config.excludedGAVs)
        for gat in artifactList.keys():
            ga = gat.rpartition(':')[0]
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    gav = ga + ":" + version
                    if _somethingMatch(regExps, gav):
                        del artifactList[gat][priority][version]
                if not artifactList[gat][priority]:
                    del artifactList[gat][priority]
            if not artifactList[gat]:
                del artifactList[gat]
        return artifactList

    def _filterExcludedRepositories(self, artifactList):
        """
        Filter artifactList removing artifacts existing in specified repositories.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without arifacts that exists in specified repositories.
        """

        for gat in artifactList.keys():
            groupId = gat.split(':')[0]
            artifactId = gat.split(':')[1]
            artifactType = gat.split(':')[2]
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    artifact = MavenArtifact(groupId, artifactId, artifactType, version)
                    if _isArtifactInRepos(self.config.excludedRepositories, artifact):
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
            for priority in sorted(artifactList[gat].keys()):
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

    def _filterMultipleVersions(self, artifactList):
        regExps = _getRegExpsFromStrings(self.config.multiVersionGAs)
        for gat in artifactList.keys():
            if _somethingMatch(regExps, gat):
                continue

            priorities = sorted(artifactList[gat].keys())
            priority = priorities[0]
            versions = artifactList[gat][priority].keys()
            if len(versions) > 1:  # list of 1 is sorted by definition
                versions = _sortVersionsWithAtlas(versions)
            for version in versions[1:]:
                del artifactList[gat][priority][version]
            for priority in priorities[1:]:
                del artifactList[gat][priority]
        return artifactList


def _getRegExpsFromStrings(strings):
    regExps = []
    for s in strings:
        regExps.append(re.compile(maven_repo_util.transformAsterixStringToRegexp(s)))
    return regExps


def _sortVersionsWithAtlas(versions):
    """
    Returns sorted list of given verisons using Atlas versionSorter

    :param versions: versions to sort.
    :returns: sorted versions.
    """
    versionSortedDir = "versionSorter/"
    jarLocation = versionSortedDir + "target/versionSorter-1.0-SNAPSHOT.jar"
    if not os.path.isfile(jarLocation):
        logging.debug("Version sorter jar '%s' not found, running 'mvn clean package' in '%s'",
                      jarLocation,
                      versionSortedDir)
        Popen(["mvn", "clean", "package"], cwd=versionSortedDir).wait()
    args = ["java", "-jar", jarLocation] + versions
    ret = Popen(args, stdout=PIPE).communicate()[0].split('\n')[::-1]
    ret.remove("")
    return ret


def _somethingMatch(regexs, string):
    """
    Returns True if at least one of regular expresions from specified list matches string.

    :param regexs: list of regular expresions
    :param filename: string to match
    :returns: True if at least one of the regular expresions matched the string.
    """

    for regex in regexs:
        if regex.match(string):
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
        url = maven_repo_util.slashAtTheEnd(repository) + artifact.getDirPath()
        if maven_repo_util.urlExists(url):
            return True
    return False
