#!/usr/bin/env python

import logging
from configuration import Configuration
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

    # produce the filtered GA(T)V list
    #TODO

    logging.info("Done")


def main():
    # Set up logging
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    createRepo()


if __name__ == '__main__':
    main()
