#!/usr/bin/env python

import logging
from configuration import Configuration
from artifact_list_builder import ArtifactListBuilder
from filter import Filter
from maven_artifact import MavenArtifact


def generateArtifactList(options):
    """
    Generates artifact "list" from sources defined in the given configuration in options. The result
    is dictionary with following structure:

    <repo url> (string)
      L artifacts (list of MavenArtifact)
    """
    # load configuration
    logging.info("Loading configuration...")
    config = Configuration()
    config.load(options)

    # build list
    logging.info("Building artifact list...")
    listBuilder = ArtifactListBuilder(config)
    artifactList = listBuilder.buildList()
    logging.debug("Generated %d GATs in the list.", len(artifactList))

    #filter list
    logging.info("Filtering artifact list...")
    listFilter = Filter(config)
    artifactList = listFilter.filter(artifactList)

    logging.info("Artifact list generation done")

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

    generateArtifactList()

    # TODO: pkocandr - process the output and hand it over somehow


if __name__ == '__main__':
    main()
