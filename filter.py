import re
import logging
from itertools import groupby
from multiprocessing.pool import ThreadPool

import maven_repo_util
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

        logging.debug("Filtering artifacts with excluded GAVs.")
        regExps = maven_repo_util.getRegExpsFromStrings(self.config.excludedGAVs)
        for gat in artifactList.keys():
            ga = gat.rpartition(':')[0]
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    gav = ga + ":" + version
                    if maven_repo_util.somethingMatch(regExps, gav):
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

        logging.debug("Filtering artifacts contained in excluded repositories.")

        pool = ThreadPool(maven_repo_util.MAX_THREADS)
        # Contains artifact to be removed
        delArtifacts = []
        for gat in artifactList.keys():
            groupId = gat.split(':')[0]
            artifactId = gat.split(':')[1]
            artifactType = gat.split(':')[2]
            for priority in artifactList[gat].keys():
                for version in artifactList[gat][priority].keys():
                    artifact = MavenArtifact(groupId, artifactId, artifactType, version)
                    pool.apply_async(
                        _artifactInRepos,
                        [self.config.excludedRepositories, artifact, priority, delArtifacts]
                    )
                if not artifactList[gat][priority]:
                    del artifactList[gat][priority]
            if not artifactList[gat]:
                del artifactList[gat]

        # Close the pool and wait for the workers to finnish
        pool.close()
        pool.join()
        for artifact, priority in delArtifacts:
            del artifactList[artifact.getGAT()][priority][artifact.version]

        return artifactList

    def _filterDuplicates(self, artifactList):
        """
        Filter artifactList removing duplicate artifacts.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without duplicate arifacts from lower priorities.
        """

        logging.debug("Filtering duplicate artifacts.")
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
        logging.debug("Filtering multi-version artifacts to have just a single version.")
        regExps = maven_repo_util.getRegExpsFromStrings(self.config.multiVersionGAs, False)

        removeT = lambda gat: re.sub('\:[^:]+$', '', gat)
        for ga, gats in groupby(sorted(artifactList.keys()), removeT):
            gats = list(gats)
            if maven_repo_util.somethingMatch(regExps, ga):
                continue

            # Gather all priorities from all types
            priorities = set()
            for gat in gats:
                priorities.update(artifactList[gat].keys())
            priorities = sorted(priorities)
            priority = priorities[0]
            # Gather all versions from all types
            versions = set()
            for gat in gats:
                # update versions only if this gat contains highest priority
                versions.update(artifactList[gat].get(priority, {}).keys())
            versions = list(versions)

            if len(versions) > 1:  # list of 1 is sorted by definition
                versions = maven_repo_util._sortVersionsWithAtlas(versions)

            # Remove version, priorities and gats from artifactList as necessary
            for gat in gats:
                for version in versions[1:]:
                    artifactList[gat].get(priority, {}).pop(version, None)
                for p in priorities[1:]:
                    artifactList[gat].pop(p, None)

                if not artifactList[gat] or not artifactList[gat][priority]:
                    del artifactList[gat]  # all versions or priorities were removed
        return artifactList


def _artifactInRepos(repositories, artifact, priority, artifacts):
    """
    Checks if artifact is available in one of the repositories, if so, appends
    it with priority in list of pairs - artifacts. Used for multithreading.

    :param repositories: list of repository urls
    :param artifact: searched MavenArtifact
    :param priority: value of dictionary artifacts
    :param artifacts: list with (artifact, priority) tuples
    """
    for repoUrl in repositories:
        if maven_repo_util.gavExists(repoUrl, artifact):
            #Critical section?
            artifacts.append((artifact, priority))
            break
