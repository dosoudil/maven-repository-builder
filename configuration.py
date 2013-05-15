import json

class Configuration:
    """Class for loading configuration"""

    resultFilename = ''
    generateMetadata = ''
    singleVersion = ''
    artifactSources = []
    excludedGAVs = []
    excludedRepositories = []
    excludedFilePatterns = []

    def __init__(self, filename):
        self.loadConfig(filename)

    def loadConfig(self, filename, rewrite=True):
        data=json.load(open(filename))

        if 'include-high-priority' in data:
            self.loadConfig(data['include-high-priority'],False)

        if (rewrite or self.resultFilename == '') and 'result-filename' in data:
            self.resultFilename = data['result-filename']

        if (rewrite or self.generateMetadata == '') and 'generate-metadata' in data:
            self.generateMetadata = data['generate-metadata']

        if (rewrite or self.singleVersion == '') and 'single-version' in data:
            self.singleVersion = data['single-version']

        if 'artifact-sources' in data:
            self.artifactSources.extend(data['artifact-sources'])

        if 'excluded-gavs' in data:
            self.excludedGAVs.extend(data['excluded-gavs'])

        if 'excluded-repositories' in data:
            self.excludedRepositories.extend(data['excluded-repositories'])

        if 'excluded-file-patterns' in data:
            self.excludedFilePatterns.extend(data['excluded-file-patterns'])

        if 'include-low-priority' in data:
            self.loadConfig(data['include-low-priority'],False)

