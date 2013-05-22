import json
import os
import logging
from optparse import OptionParser

class Configuration:
    """
    Class holding Maven Repository Builder configuration. It can be loaded
    from a json configuration file.
    """

    resultRepoName = ''
    generateMetadata = ''
    singleVersion = ''
    artifactSources = []
    excludedGAVs = []
    excludedRepositories = []
    excludedFilePatterns = []
    tempdir = '/tmp/maven-repo-builder/'
    targetdir = './'

    def load(self):
        """ Load confiugration from command line arguments """
        parser = OptionParser(usage = '%prog [options]')
        parser.add_option('-c', '--config', dest = 'config',
                          help = 'Configuration file to use to drive the repository builder')
        parser.add_option('-t', '--tempdir', dest = 'tempdir',
                          help = 'Temporary directory where repository will be built',
                          default = '/tmp/maven-repo-builder/')
        parser.add_option('--targetdir', dest = 'targetdir',
                          help = 'Target directory where built repository archive will be placed')
        (opts, args) = parser.parse_args()

        if opts.config is None:
            logging.error('You must specify a config file')
            os._exit(1)

        self._loadFromFile(opts.config)
        self.tempdir = opts.tempdir
        if not opts.targetdir is None:
            self.targetdir = opts.targetdir


    def _loadFromFile(self, filename, rewrite = True):
        """ Load confiugration from json confi file. """
        data=json.load(open(filename))

        if 'include-high-priority' in data and data['include-high-priority']:
            self._loadFromFile(data['include-high-priority'], True)

        if (rewrite or self.resultRepoName == '') and 'result-repo-name' in data:
            self.resultRepoName = data['result-repo-name']

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

        if 'include-low-priority' in data and data['include-low-priority']:
            self._loadFromFile(data['include-low-priority'], False)
