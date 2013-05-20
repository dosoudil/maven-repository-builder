#!/usr/bin/env python

import urllib
import urlparse
from configuration import Configuration
from artifact_list_builder import ArtifactListBuilder


def createRepo():

    # load configuration
    config = Configuration()
    config.load()

    # build list
    listBuilder = ArtifactListBuilder(config)
    artifactList = listBuilder.buildList()

    #filter list
    # TODO

    # fetch artifacts
    # TODO

    # package repository
    # TODO

    # test repository
    # TODO


def main():

    createRepo()


if __name__ == '__main__':
    main()
