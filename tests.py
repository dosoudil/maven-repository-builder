#!/usr/bin/env python

""" tests.py: Unit tests for maven repo builder and related tools"""

import logging
import os
import tempfile
import unittest

import maven_repo_util

from maven_artifact import MavenArtifact

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
            logging.debug('Removing temp local file: ' + localfilename)
            os.remove(localfilename)

    def test_bad_urls(self):
        url = "junk://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_util.download(url)

        url = "sadjfasfjsl"
        maven_repo_util.download(url)

        url = "http://1234/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_util.download(url)

    def test_http_404(self):
        url = "http://repo1.maven.org/maven2/somefilethatdoesnotexist"   
        code = maven_repo_util.download(url)
        self.assertEqual(code, 404)

    def test_maven_artifact(self):
        artifact1 = MavenArtifact("org.jboss:jboss-parent:pom:10")
        self.assertEqual(artifact1.groupId, "org.jboss")
        self.assertEqual(artifact1.artifactId, "jboss-parent")
        self.assertEqual(artifact1.version, "10")
        self.assertEqual(artifact1.getArtifactType(), "pom")
        self.assertEqual(artifact1.getClassifier(), "")
        self.assertEqual(artifact1.getArtifactFilename(), "jboss-parent-10.pom")
        self.assertEqual(artifact1.getArtifactFilepath(), "org/jboss/jboss-parent/10/jboss-parent-10.pom")

        artifact2 = MavenArtifact("org.jboss:jboss-foo:jar:1.0")
        self.assertEqual(artifact2.getArtifactFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0.jar")
        self.assertEqual(artifact2.getPomFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0.pom")
        self.assertEqual(artifact2.getSourcesFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0-sources.jar")

        artifact3 = MavenArtifact("org.jboss:jboss-test:jar:client:2.0.0.Beta1")
        self.assertEqual(artifact3.getClassifier(), "client")
        self.assertEqual(artifact3.getArtifactFilename(), "jboss-test-2.0.0.Beta1-client.jar")
        self.assertEqual(artifact3.getArtifactFilepath(), "org/jboss/jboss-test/2.0.0.Beta1/jboss-test-2.0.0.Beta1-client.jar")


if __name__ == '__main__':
    unittest.main()

