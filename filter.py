import logging
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

        if self.config.excludedGAVs:
            artifactList = self._filterExcludedGAVs(artifactList)

        if self.config.excludedTypes:
            artifactList = self._filterExcludedTypes(artifactList)

        artifactList = self._filterDuplicates(artifactList)

        if self.config.singleVersion:
            artifactList = self._filterMultipleVersions(artifactList)

        if self.config.excludedRepositories:
            artifactList = self._filterExcludedRepositories(artifactList)

        return artifactList

    def _filterExcludedGAVs(self, artifactList):
        """
        Filter artifactList removing specified GAVs.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without artifacts that matched specified GAVs.
        """

        logging.debug("Filtering artifacts with excluded GAVs.")
        regExps = maven_repo_util.getRegExpsFromStrings(self.config.excludedGAVs)
        for ga in artifactList.keys():
            for priority in artifactList[ga].keys():
                for version in artifactList[ga][priority].keys():
                    gav = ga + ":" + version
                    if maven_repo_util.somethingMatch(regExps, gav):
                        del artifactList[ga][priority][version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]
        return artifactList

    def _filterExcludedTypes(self, artifactList):
        '''
        Filter artifactList removing GAVs with specified main types only, otherwise keeping GAVs with
        not-excluded artifact types only.

        :param artifactList: artifactList to be filtered.
        :param exclTypes: list of excluded types
        :returns: artifactList without artifacts that matched specified types and had no other main types.
        '''
        logging.debug("Filtering artifacts with excluded types.")
        regExps = maven_repo_util.getRegExpsFromStrings(self.config.gatcvWhitelist)
        exclTypes = self.config.excludedTypes
        for ga in artifactList.keys():
            for priority in artifactList[ga].keys():
                for version in artifactList[ga][priority].keys():
                    artSpec = artifactList[ga][priority][version]
                    for artType in list(artSpec.artTypes.keys()):
                        artTypeObj = artSpec.artTypes[artType]
                        if artType in exclTypes:
                            classifiers = artTypeObj.classifiers
                            (groupId, artifactId) = ga.split(':')
                            for classifier in list(classifiers):
                                art = MavenArtifact(groupId, artifactId, artType, version, classifier)
                                gatcv = art.getGATCV()
                                if not maven_repo_util.somethingMatch(regExps, gatcv):
                                    classifiers.remove(classifier)
                            if not classifiers:
                                del(artSpec.artTypes[artType])
                    noMain = True
                    for artType in artSpec.artTypes.keys():
                        artTypeObj = artSpec.artTypes[artType]
                        if artTypeObj.mainType:
                            noMain = False
                            break
                    if not artSpec.artTypes or noMain:
                        del artifactList[ga][priority][version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]
        return artifactList

    def _filterExcludedRepositories(self, artifactList):
        """
        Filter artifactList removing artifacts existing in specified repositories.

        :param artifactList: artifactList to be filtered.
        :returns: artifactList without artifacts that exists in specified repositories.
        """

        logging.debug("Filtering artifacts contained in excluded repositories.")

        pool = ThreadPool(maven_repo_util.MAX_THREADS)
        # Contains artifact to be removed
        delArtifacts = []
        for ga in artifactList.keys():
            groupId = ga.split(':')[0]
            artifactId = ga.split(':')[1]
            for priority in artifactList[ga].keys():
                for version in artifactList[ga][priority].keys():
                    artifact = MavenArtifact(groupId, artifactId, "pom", version)
                    pool.apply_async(
                        _artifactInRepos,
                        [self.config.excludedRepositories, artifact, priority, delArtifacts]
                    )
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]

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
        :returns: artifactList without duplicate artifacts from lower priorities.
        """

        logging.debug("Filtering duplicate artifacts.")
        for ga in artifactList.keys():
            for priority in sorted(artifactList[ga].keys()):
                for version in artifactList[ga][priority].keys():
                    for pr in artifactList[ga].keys():
                        if pr <= priority:
                            continue
                        if version in artifactList[ga][pr]:
                            del artifactList[ga][pr][version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]
        return artifactList

    def _filterMultipleVersions(self, artifactList):
        logging.debug("Filtering multi-version artifacts to have just a single version.")
        regExps = maven_repo_util.getRegExpsFromStrings(self.config.multiVersionGAs, False)

        for ga in sorted(artifactList.keys()):
            if maven_repo_util.somethingMatch(regExps, ga):
                continue

            # Gather all priorities
            priorities = sorted(artifactList[ga].keys())
            priority = priorities[0]
            # Gather all versions
            versions = list(artifactList[ga][priority].keys())

            if len(versions) > 1:  # list of 1 is sorted by definition
                versions = maven_repo_util._sortVersionsWithAtlas(versions)

            # Remove version, priorities and gats from artifactList as necessary
            for version in versions[1:]:
                artifactList[ga][priority].pop(version, None)
            for p in priorities[1:]:
                artifactList[ga].pop(p, None)

        return artifactList


def _artifactInRepos(repositories, artifact, priority, artifacts):
    """
    Checks if artifact is available in one of the repositories, if so, appends
    it with priority in list of pairs - artifacts. Used for multi-threading.

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
