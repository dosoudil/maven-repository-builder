#!/usr/bin/env python

import re
import koji
import os
import urllib
import urlparse
from configuration import Configuration
from maven_artifact import MavenArtifact
from artifact_list_builder import ArtifactListBuilder


def createRepo():

    # load configuration
    config = Configuration()
    config.load()
    config.tempdir = tempdir

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
