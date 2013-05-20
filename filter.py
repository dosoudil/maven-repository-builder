from maven_artifact import MavenArtifact

class Filter:


    def __init__(self, configuration):


    def filter(self, artifactList):
        artifactList = self._filterExcludedGAVs(artiactList, configuration.excludedGavs)
        artifactList = self._filterExcludedFilePatterns(artifactList, configuration.excludedFilePatterns)
        artifactList = self._filterExcludedRepositories(artifactList, configuration.excludedRepositories)
        return artifactList

    def _filterExcludedGAVs(artiactList, gavs):
        for gav in gavs:
            artifact.add(MavenArtifact.createFromGAV(gav))
            ga = artifact.getGA()
            if not ga in artifactList: continue
            for priority in artifactList[ga]:
                if not artifact.version in artifactList[ga][priority]: continue
                del artifactList[ga][priority][artifact.version]
        return artifactList

    def _filterExcludedFilePatterns(artifactList, patterns):
        pass

    def _filterExcludedRepositories(artifactList, repositories):
        pass
