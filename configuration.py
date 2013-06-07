import json
import sys
import logging
import maven_repo_util


class Configuration:
    """
    Class holding Artifact List Generator configuration. It can be loaded
    from a json configuration file.
    """

    generateMetadata = None
    singleVersion = None
    artifactSources = []
    excludedGAVs = []
    excludedRepositories = []
    multiVersionGAs = []

    def load(self, opts):
        """
        Load confiugration from command line arguments

        :param opts: options parsed by an OptionParser
        """

        if opts.config is None:
            logging.error('You must specify a config file')
            sys.exit(1)

        self._loadFromFile(opts.config)
        self._setDefaults()
        self._validate()

    def _setDefaults(self):
        if self.generateMetadata is None:
            self.generateMetadata = False
        if self.singleVersion is None:
            self.singleVersion = True

    def _validate(self):
        valid = True
        if self.generateMetadata is None:
            logging.error("Option generate-metadata not set in configuration file.")
            valid = False
        if self.singleVersion is None:
            logging.error("Option single-version not set in configuration file.")
            valid = False
        if not self.artifactSources:
            logging.error("No artifact-sources set in configuration file.")
            valid = False
        if not valid:
            sys.exit(1)

    def _loadFromFile(self, filename, rewrite=True):
        """ Load confiugration from json config file. """
        data = json.load(open(filename))

        if 'include-high-priority' in data and data['include-high-priority']:
            self._loadFromFile(data['include-high-priority'], True)

        if (rewrite or self.resultRepoName is None) and 'result-repo-name' in data:
            self.resultRepoName = data['result-repo-name']

        if (rewrite or self.generateMetadata is None) and 'generate-metadata' in data:
            self.generateMetadata = maven_repo_util.str2bool(data['generate-metadata'])

        if (rewrite or self.singleVersion is None) and 'single-version' in data:
            self.singleVersion = maven_repo_util.str2bool(data['single-version'])

        if 'artifact-sources' in data:
            self._loadArtifactSources(data['artifact-sources'])

        if 'excluded-gav-patterns-ref' in data:
            for filename in data['excluded-gav-patterns-ref']:
                self.excludedGAVs.extend(self._loadFlatFile(filename))

        if 'excluded-repositories' in data:
            self.excludedRepositories.extend(data['excluded-repositories'])

        if 'multi-version-ga-patterns-ref' in data:
            for filename in data['multi-version-ga-patterns-ref']:
                self.multiVersionGAs.extend(self._loadFlatFile(filename))

        if 'multi-version-ga-patterns' in data:
            self.multiVersionGAs.extend(data['multi-version-ga-patterns'])

        if 'include-low-priority' in data and data['include-low-priority']:
            self._loadFromFile(data['include-low-priority'], False)

    def _loadArtifactSources(self, artifactSources):
        for source in artifactSources:
            if not 'type' in source:
                logging.error("Source doesn't have type.\n %s", str(source))
                sys.exit(1)
            if source['type'] == 'mead-tag':
                source['included-gav-patterns'] = self._loadFlatFileBySourceParameter(source,
                        'included-gav-patterns-ref')
            elif source['type'] == 'dependency-list':
                source['repo-url'] = self._getRepoUrl(source)
                source['top-level-gavs'] = self._loadFlatFileBySourceParameter(source, 'top-level-gavs-ref')
            elif source['type'] == 'repository':
                source['repo-url'] = self._getRepoUrl(source)
                source['included-gav-patterns'] = self._loadFlatFileBySourceParameter(source,
                        'included-gav-patterns-ref')
            self.artifactSources.append(source)

    def _loadFlatFileBySourceParameter(self, source, parameter):
        if parameter in source:
            return self._loadFlatFile(source[parameter])
        else:
            return []

    def _loadFlatFile(self, filename):
        if filename:
            with open(filename, "r") as openedfile:
                return openedfile.readlines()

    def _getRepoUrl(self, source):
        if not 'repo-url' in source:
            logging.error("Source %s must have specified repo-url.", source['type'])
            sys.exit(1)
        if isinstance(source['repo-url'], basestring):
            return [source['repo-url']]
        else:
            return source['repo-url']
