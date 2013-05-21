import re
import mrbutils
from maven_artifact import MavenArtifact

class Filter:

    def __init__(self, config):
        self.config= config

    def filter(self, artifactList):
        artifactList = self._filterExcludedGAVs(artifactList, self.config.excludedGAVs)
        artifactList = self._filterExcludedFilePatterns(artifactList, self.config.excludedFilePatterns)
        artifactList = self._filterExcludedRepositories(artifactList, self.config.excludedRepositories)
        return artifactList

    def _filterExcludedGAVs(self, artifactList, gavs):
        for gav in gavs:
            artifact = MavenArtifact.createFromGAV(gav)
            ga = artifact.getGA()
            if not ga in artifactList: continue
            for priority in artifactList[ga].keys():
                if not artifact.version in artifactList[ga][priority]: continue
                del artifactList[ga][priority][artifact.version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]
        return artifactList

    def _filterExcludedFilePatterns(self, artifactList, patterns):
        regexs = []
        for pattern in patterns:
            regexs.append(re.compile(pattern))
        for ga in artifactList.keys():
            for priority in artifactList[ga].keys():
                for version in artifactList[ga][priority].keys():
                    artifactList[ga][priority][version][:] = [ filename for filename in artifactList[ga][priority][version] if not _somethingMatch(regexs, filename) ]
                    if not artifactList[ga][priority][version]:
                        del artifactList[ga][priority][version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not artifactList[ga]:
                del artifactList[ga]
        return artifactList

    def _filterExcludedRepositories(self, artifactList, repositories):
        for ga in artifactList.keys():
            groupId = ga.split(':')[0]
            artifactId = ga.split(':')[1]
            for priority in artifactList[ga].keys():
                for version in artifactList[ga][priority].keys():
                    artifact = MavenArtifact(groupId, artifactId, version)
                    if _isArtifactInRepos(repositories, artifact):
                        del artifactList[ga][priority][version]
                if not artifactList[ga][priority]:
                    del artifactList[ga][priority]
            if not not artifactList[ga]:
                del artifactList[ga]

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
