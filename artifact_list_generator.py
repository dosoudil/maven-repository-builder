#!/usr/bin/env python

import logging
import optparse
from configuration import Configuration
from artifact_list_builder import ArtifactListBuilder
from filter import Filter
from maven_artifact import MavenArtifact
import maven_repo_util


def _generateArtifactList(options):
    # load configuration
    logging.info("Loading configuration...")
    config = Configuration()
    config.load(options)

    # build list
    logging.info("Building artifact list...")
    listBuilder = ArtifactListBuilder(config)
    artifactList = listBuilder.buildList()

    logging.debug("Generated list contents:")
    for gat in artifactList:
        priorityList = artifactList[gat]
        for priority in priorityList:
            versionList = priorityList[priority]
            for version in versionList:
                logging.debug("  %s:%s", gat, version)

    #filter list
    logging.info("Filtering artifact list...")
    listFilter = Filter(config)
    artifactList = listFilter.filter(artifactList)

    logging.debug("Filtered list contents:")
    for gat in artifactList:
        priorityList = artifactList[gat]
        for priority in priorityList:
            versionList = priorityList[priority]
            for version in versionList:
                logging.debug("  %s:%s", gat, version)

    logging.info("Artifact list generation done")
    return artifactList


def generateArtifactList(options):
    """
    Generates artifact "list" from sources defined in the given configuration in options. The result
    is dictionary with following structure:

    <repo url> (string)
      L artifacts (list of MavenArtifact)
    """

    options.allclassifiers = (options.classifiers == '*')

    artifactList = _generateArtifactList(options)
    #build sane structure - url to MavenArtifact list
    urlToMAList = {}
    for gat in artifactList:
        priorityList = artifactList[gat]
        for priority in priorityList:
            versionList = priorityList[priority]
            for version in versionList:
                artSpec = versionList[version]
                url = artSpec.url
                urlToMAList.setdefault(url, []).append(MavenArtifact.createFromGAV(gat + ":" + version))
                if options.allclassifiers and artSpec.classifiers:
                    for classifier in artSpec.classifiers:
                        urlToMAList[url].append(MavenArtifact.createFromGAV(gat + ":" + classifier + ":" + version))

    return urlToMAList


def main():
    description = "Generate artifact list from sources defined in the given congiguration file"
    cliOptParser = optparse.OptionParser(usage="Usage: %prog -c CONFIG", description=description)
    cliOptParser.add_option('-c', '--config', dest='config',
            help='Configuration file to use for generation of an artifact list for the repository builder')
    cliOptParser.add_option('-l', '--loglevel',
            default='info',
            help='Set the level of log output.  Can be set to debug, info, warning, error, or critical')
    cliOptParser.add_option('-L', '--logfile',
            help='Set the file in which the log output should be written.')
    (options, args) = cliOptParser.parse_args()

    # Set the log level
    maven_repo_util.setLogLevel(options.loglevel, options.logfile)

    options.allclassifiers = False
    artifactList = _generateArtifactList(options)

    maven_repo_util.printArtifactList(artifactList)


if __name__ == '__main__':
    main()
