#!/usr/bin/env python

""" tests.py: Unit tests for maven repo builder and related tools"""

import logging
import os
import tempfile
import unittest

import maven_repo_util

class Tests(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)

    def test_url_download(self):
        # make sure the shuffled sequence does not lose any elements
        url = "http://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.pom"
        tempDownloadDir = tempfile.mkdtemp()
        filepath = os.path.join(tempDownloadDir, "downloadfile.txt")
        self.assertFalse(os.path.exists(filepath), "Download file alread exists: " + filepath )
        maven_repo_util.download(url, filepath)
        self.assertTrue(os.path.exists(filepath), "File not downloaded")

        maven_repo_util.download(url)
        localfilename = "jboss-parent-10.pom"
        self.assertTrue(os.path.exists(localfilename))
        if os.path.exists(localfilename):
            os.remove(localfilename)

if __name__ == '__main__':
    unittest.main()
