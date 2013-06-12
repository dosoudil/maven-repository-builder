#!/usr/bin/env python

import logging
import optparse
from configuration import Configuration
from artifact_list_builder import ArtifactListBuilder
from filter import Filter
from maven_artifact import MavenArtifact
import maven_repo_util as mrbutils


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

    artifactList = _generateArtifactList(options)
    #build sane structure - url to MavenArtifact list
    urlToMAList = {}
    for gat in artifactList:
        prioList = artifactList[gat]
        for priority in prioList:
            verList = prioList[priority]
            for version in verList:
                url = verList[version]
                urlToMAList.setdefault(url, []).append(MavenArtifact.createFromGAV(gat + ":" + version))

    return urlToMAList


def main():
    # Set up logging
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    description = "Generate artifact list from sources defined in the given congiguration file"
    cliOptParser = optparse.OptionParser(usage="Usage: %prog -c CONFIG", description=description)
    cliOptParser.add_option('-c', '--config', dest='config',
            help='Configuration file to use for generation of an artifact list for the repository builder')
    (options, args) = cliOptParser.parse_args()

    artifactList = _generateArtifactList(options)

    mrbutils.printArtifactList(artifactList)


if __name__ == '__main__':
    main()
