#!/usr/bin/env python

import logging
from configuration import Configuration
from download import fetchArtifacts
from artifact_list_builder import ArtifactListBuilder
from filter import Filter


def createRepo():

    # load configuration
    logging.info("Loading configuration...")
    config = Configuration()
    config.load()

    # build list
    logging.info("Building artifact list...")
    listBuilder = ArtifactListBuilder(config)
    artifactList = listBuilder.buildList()

    #filter list
    logging.info("Filtering artifact list...")
    listFilter = Filter(config)
    artifactList = listFilter.filter(artifactList)

    # fetch artifacts
    logging.info("Retrieving artifacts...")
    fetchArtifacts(artifactList, config)

    # package repository
    # TODO

    # test repository
    # TODO

    logging.info("Done")


def main():
    # Set up logging
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    createRepo()


if __name__ == '__main__':
    main()
