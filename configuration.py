import json
import logging
import os
import sys

import maven_repo_util


class Configuration:
    """
    Class holding Artifact List Generator configuration. It can be loaded
    from a json configuration file.
    """

    ALL_CLASSIFIERS_VALUE = "__all__"

    singleVersion = None
    artifactSources = []
    excludedGAVs = []
    excludedRepositories = []
    excludedTypes = []
    multiVersionGAs = []
    _configFiles = set()
    addClassifiers = set()
    gatcvWhitelist = []

    def load(self, opts):
        """
        Load configuration from command line arguments using requested config file.

        :param opts: options parsed by an OptionParser
        """

        if opts.config is None:
            logging.error('You must specify a config file')
            sys.exit(1)

        self.addClassifiers = self._parseClassifiers(opts.classifiers)
        self.excludedTypes = opts.excludedtypes.split(':')
        if opts.whitelist:
            self.gatcvWhitelist = maven_repo_util.loadArtifactFile(opts.whitelist)

        self.loadFromFile(opts.config)

    def create(self, opts, args):
        """
        Creates configuration from command line parameters like url, artifact list files etc.

        :param opts: options parsed by an OptionParser
        """
        self.singleVersion = False
        includedGatcvs = []
        for filename in args:
            includedGatcvs.extend(maven_repo_util.loadArtifactFile(filename))
        self.artifactSources = [{
            "type": "repository",
            "repo-url": [opts.url],
            "included-gatcvs": includedGatcvs
        }]

        self._setDefaults()
        self._validate()

        self.addClassifiers = self._parseClassifiers(opts.classifiers)
        self.excludedTypes = opts.excludedtypes.split(':')
        if opts.whitelist:
            # TODO read the file properly (skip comments, enable regexps, ...)
            self.gatcvWhitelist = maven_repo_util.loadArtifactFile(opts.whitelist)

    def loadFromFile(self, filename):
        self._loadFromFile(filename)
        self._setDefaults()
        self._validate()

    def isAllClassifiers(self):
        """
        Checks if all available classifiers should be downloaded.
        """
        return self.addClassifiers == self.ALL_CLASSIFIERS_VALUE

    def _setDefaults(self):
        if self.singleVersion is None:
            self.singleVersion = True
        for source in self.artifactSources:
            if source['type'] == 'dependency-list':
                if 'recursive' not in source:
                    source['recursive'] = True
                if 'skip-missing' not in source:
                    source['skip-missing'] = True
            elif source['type'] == 'dependency-graph':
                if 'wsid' not in source:
                    source['wsid'] = None
                if 'excluded-sources' not in source:
                    source['excluded-sources'] = []
                if 'preset' not in source:
                    source['preset'] = None
                if 'patcher-ids' not in source:
                    source['patcher-ids'] = []
            elif source['type'] == 'repository':
                if 'included-gav-patterns' not in source:
                    source['included-gav-patterns'] = []

    def _validate(self):
        valid = True
        if self.singleVersion is None:
            logging.error("Option single-version not set in configuration file.")
            valid = False
        if not self.artifactSources:
            logging.error("No artifact-sources set in configuration file.")
            valid = False
        else:
            for source in self.artifactSources:
                if source['type'] == 'dependency-graph':
                    if 'aprox-url' not in source:
                        logging.error("No aprox-url specified for source with type dependency-graph.")
                        valid = False
                    if 'source-key' not in source:
                        logging.error("No source-key specified for source with type dependency-graph.")
                        valid = False
                    if not len(source['top-level-gavs']):
                        logging.error("No top-level GAV specified for source with type dependency-graph.")
                        valid = False
        if not valid:
            sys.exit(1)

    def _loadFromFile(self, filename, rewrite=True):
        """ Load configuration from json config file. """
        logging.debug("Loading configuration file %s", filename)
        if filename in self._configFiles:
            raise Exception("Config file '%s' is already included." % filename +
                            " Check your config files for circular inclusions.")
        self._configFiles.add(filename)
        data = json.load(open(filename))

        filePath = os.path.dirname(filename)
        if filePath:
            filePath += '/'

        if 'include-high-priority' in data and data['include-high-priority']:
            inclFile = self._getRelativeFilename(data['include-high-priority'], filePath)
            self._loadFromFile(inclFile, True)

        if (rewrite or self.singleVersion is None) and 'single-version' in data:
            self.singleVersion = maven_repo_util.str2bool(data['single-version'])

        if 'artifact-sources' in data:
            self._loadArtifactSources(data['artifact-sources'], filePath)

        if 'excluded-gav-patterns-ref' in data:
            for filename in data['excluded-gav-patterns-ref']:
                relFilename = self._getRelativeFilename(filename, filePath)
                self.excludedGAVs.extend(maven_repo_util.loadFlatFile(relFilename))

        if 'excluded-repositories' in data:
            self.excludedRepositories.extend(data['excluded-repositories'])

        if 'multi-version-ga-patterns-ref' in data:
            for filename in data['multi-version-ga-patterns-ref']:
                relFilename = self._getRelativeFilename(filename, filePath)
                self.multiVersionGAs.extend(maven_repo_util.loadFlatFile(relFilename))

        if 'multi-version-ga-patterns' in data:
            self.multiVersionGAs.extend(data['multi-version-ga-patterns'])

        if 'include-low-priority' in data and data['include-low-priority']:
            inclFile = self._getRelativeFilename(data['include-low-priority'], filePath)
            self._loadFromFile(inclFile, False)

    def _loadArtifactSources(self, artifactSources, filePath):
        for source in artifactSources:
            if not 'type' in source:
                logging.error("Source doesn't have type.\n %s", str(source))
                sys.exit(1)

            if source['type'] == 'mead-tag':
                source['included-gav-patterns'] = self._loadFlatFileBySourceParameter(source,
                        'included-gav-patterns-ref', filePath)

            elif source['type'] == 'dependency-list':
                if 'recursive' in source:
                    source['recursive'] = maven_repo_util.str2bool(source['recursive'])
                if 'skip-missing' in source:
                    source['skip-missing'] = maven_repo_util.str2bool(source['skip-missing'])
                source['repo-url'] = self._getRepoUrl(source)
                source['top-level-gavs'] = self._loadFlatFileBySourceParameter(source, 'top-level-gavs-ref',
                        filePath)

            elif source['type'] == 'dependency-graph':
                source['top-level-gavs'] = self._loadFlatFileBySourceParameter(source, 'top-level-gavs-ref',
                        filePath)

            elif source['type'] == 'repository':
                source['repo-url'] = self._getRepoUrl(source)
                source['included-gav-patterns'] = self._loadFlatFileBySourceParameter(source,
                        'included-gav-patterns-ref', filePath)
                source['included-gatcvs'] = self._loadArtifactFileBySourceParameter(source, 'included-gatcvs-ref',
                        filePath)

            self.artifactSources.append(source)

    def _loadFlatFileBySourceParameter(self, source, parameter, filePath):
        if parameter in source:
            relFilename = self._getRelativeFilename(source[parameter], filePath)
            return maven_repo_util.loadFlatFile(relFilename)
        else:
            return []

    def _loadArtifactFileBySourceParameter(self, source, parameter, filePath):
        if parameter in source:
            relFilename = self._getRelativeFilename(source[parameter], filePath)
            return maven_repo_util.loadArtifactFile(relFilename)
        else:
            return []

    def _getRelativeFilename(self, filename, path):
        """Checks, if the given filename has absolute path, and if not, it preppends to it given path."""
        if os.path.isabs(filename):
            return filename
        else:
            return path + filename

    def _getRepoUrl(self, source):
        if not 'repo-url' in source:
            logging.error("Source %s must have specified repo-url.", source['type'])
            sys.exit(1)
        if isinstance(source['repo-url'], basestring):
            return [source['repo-url']]
        else:
            return source['repo-url']

    def _parseClassifiers(self, classifiersString):
        """
        Parses classifiers and types from command-line argument value. The result  is list of dictionaries. Each
        dictionary contains classifier value under "classifier" key and type under "type" key. If no type is specified,
        then the value "jar" is used for key "type".

        :param classifiersString: comma-separated list of classifiers with an optional prepended type separated by colon,
                                  if no type specified, then the default type ("jar") is used
        :returns: list of dictionaries with structure e.g. {"classifiers": "sources", "type": "jar"}
        """
        if not classifiersString:
            result = []
        elif classifiersString == self.ALL_CLASSIFIERS_VALUE:
            result = self.ALL_CLASSIFIERS_VALUE
        else:
            classifiers = classifiersString.split(",")
            result = []
            if len(classifiers) == 1 and classifiers.count(":") > 1:
                for classifier in classifiersString.split(":"):
                    result.append({"classifier": classifier, "type": "jar"})
            else:
                for classifier in classifiers:
                    colonCount = classifier.count(":")
                    if colonCount == 0:
                        result.append({"classifier": classifier, "type": "jar"})
                    elif colonCount == 1:
                        parts = classifier.split(":")
                        result.append({"classifier": parts[1], "type": parts[0]})

        return result
