#!/usr/bin/env python

""" tests.py: Unit tests for maven repo builder and related tools"""

import logging
import os
import tempfile
import unittest
import copy

import maven_repo_builder

from maven_artifact import MavenArtifact
from artifact_list_builder import ArtifactListBuilder
from configuration import Configuration
from filter import Filter


class Tests(unittest.TestCase):

    artifactList = {
      "com.google.guava:guava:pom": {
        "1": {
          "1.0.0": "http://repo1.maven.org/maven2/",
          "1.0.1": "http://repo1.maven.org/maven2/",
          "1.1.0": "http://repo1.maven.org/maven2/"},
        "2": {
          "1.0.2": "http://repo2.maven.org/maven2/"},
        "3": {
          "1.2.0": "http://repo3.maven.org/maven2/",
          "1.0.0": "http://repo3.maven.org/maven2/"}},
      "org.jboss:jboss-foo:jar": {
        "1": {
          "1.0.0": "http://repo1.maven.org/maven2/",
          "1.0.1": "http://repo1.maven.org/maven2/",
          "1.1.0": "http://repo1.maven.org/maven2/"},
        "2": {
          "1.0.1": "http://repo2.maven.org/maven2/",
          "1.0.2": "http://repo2.maven.org/maven2/"}}}

    def setUp(self):
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

    def test_url_download(self):
        # make sure the shuffled sequence does not lose any elements
        url = "http://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.pom"
        tempDownloadDir = tempfile.mkdtemp()
        filepath = os.path.join(tempDownloadDir, "downloadfile.txt")
        self.assertFalse(os.path.exists(filepath), "Download file already exists: " + filepath)
        maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate, filepath)
        self.assertTrue(os.path.exists(filepath), "File not downloaded")

        maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate)
        localfilename = "jboss-parent-10.pom"
        self.assertTrue(os.path.exists(localfilename))
        if os.path.exists(localfilename):
            logging.debug('Removing temp local file: ' + localfilename)
            os.remove(localfilename)

    def test_bad_urls(self):
        url = "junk://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate)

        url = "sadjfasfjsl"
        maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate)

        url = "http://1234/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate)

    def test_http_404(self):
        url = "http://repo1.maven.org/maven2/somefilethatdoesnotexist"
        code = maven_repo_builder.download(url, maven_repo_builder._ChecksumMode.generate)
        self.assertEqual(code, 404)

    def test_maven_artifact(self):
        artifact1 = MavenArtifact.createFromGAV("org.jboss:jboss-parent:pom:10")
        self.assertEqual(artifact1.groupId, "org.jboss")
        self.assertEqual(artifact1.artifactId, "jboss-parent")
        self.assertEqual(artifact1.version, "10")
        self.assertEqual(artifact1.getArtifactType(), "pom")
        self.assertEqual(artifact1.getClassifier(), "")
        self.assertEqual(artifact1.getArtifactFilename(), "jboss-parent-10.pom")
        self.assertEqual(artifact1.getArtifactFilepath(), "org/jboss/jboss-parent/10/jboss-parent-10.pom")

        artifact2 = MavenArtifact.createFromGAV("org.jboss:jboss-foo:jar:1.0")
        self.assertEqual(artifact2.getArtifactFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0.jar")
        self.assertEqual(artifact2.getPomFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0.pom")
        self.assertEqual(artifact2.getSourcesFilepath(), "org/jboss/jboss-foo/1.0/jboss-foo-1.0-sources.jar")

        artifact3 = MavenArtifact.createFromGAV("org.jboss:jboss-test:jar:client:2.0.0.Beta1")
        self.assertEqual(artifact3.getClassifier(), "client")
        self.assertEqual(artifact3.getArtifactFilename(), "jboss-test-2.0.0.Beta1-client.jar")
        self.assertEqual(artifact3.getArtifactFilepath(),
                "org/jboss/jboss-test/2.0.0.Beta1/jboss-test-2.0.0.Beta1-client.jar")

        artifact4 = MavenArtifact.createFromGAV("org.acme:jboss-bar:jar:1.0-alpha-1:compile")
        self.assertEqual(artifact4.getArtifactFilepath(), "org/acme/jboss-bar/1.0-alpha-1/jboss-bar-1.0-alpha-1.jar")

        artifact5 = MavenArtifact.createFromGAV("com.google.guava:guava:pom:r05")
        self.assertEqual(artifact5.groupId, "com.google.guava")
        self.assertEqual(artifact5.artifactId, "guava")
        self.assertEqual(artifact5.version, "r05")
        self.assertEqual(artifact5.getArtifactType(), "pom")
        self.assertEqual(artifact5.getClassifier(), "")
        self.assertEqual(artifact5.getArtifactFilename(), "guava-r05.pom")

    def test_filter_excluded_GAVs(self):
        config = Configuration()
        alf = Filter(config)

        config.excludedGAVs = ["com.google.guava:guava:1.1.0"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        alf._filterExcludedGAVs(al)
        self.assertFalse('1.1.0' in al['com.google.guava:guava:pom']['1'])

        config.excludedGAVs = ["com.google.guava:guava:1.0*"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.2' in al['com.google.guava:guava:pom']['2'])
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['3'])
        alf._filterExcludedGAVs(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('2' in al['com.google.guava:guava:pom'])
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['3'])

        config.excludedGAVs = ["com.google.guava:*"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('com.google.guava:guava:pom' in al)
        alf._filterExcludedGAVs(al)
        self.assertFalse('com.google.guava:guava:pom' in al)

    def test_filter_duplicates(self):
        config = Configuration()
        alf = Filter(config)

        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['3'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['2'])
        alf._filterDuplicates(al)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['3'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo:jar']['2'])

    def test_ArtifactListBuilder_getPrefixes(self):
        i = ["org.abc.def:qwer:1.0.1", "org.abc.def:qwer:1.2.1",
             "org.abc.def:qwera:1.*", "org.abc.def:qwera:2.0",
             "org.abc.ret:popo:2.0", "org.abc.ret:papa:*",
             "org.abc.zir:fgh:1.2.3", "org.abc.zir:fgh:*",
             "org.abc.zir:*:*", "org.abc.zar:*", "org.zui.zor*",
             "r/eu\.test\.qwe:.*:.*/", "r/eu\.trest\..*/",
             "r/com\.part[abc]\.poiu:mark:1\.0/",
             "r/ru\.uju\.mnou:jaja:1\.[23].*/"]
        o = set(["org/abc/def/qwer/1.0.1/", "org/abc/def/qwer/1.2.1/",
             "org/abc/def/qwera/", "org/abc/ret/popo/2.0/",
             "org/abc/ret/papa/", "org/abc/zir/",
             "org/abc/zar/", "org/zui/",
             "eu/test/qwe/", "eu/trest/",
             "com/", "ru/uju/mnou/jaja/"])
        config = Configuration()
        alb = ArtifactListBuilder(config)
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

        i = ["org.abc.def:qwer:1.0.1", "org.abc.def:qwer:1.2.1",
             "r/r.\..*/"]
        o = {""}
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

        i = ["org.abc.def:qwer:1.0.1", "org.abc.def:qwer:1.2.1",
             "r/(org|com).*/"]
        o = {""}
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

    def test_filter_multiple_versions(self):
        config = Configuration()
        config.singleVersion = True
        alf = Filter(config)

        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('2' in al['com.google.guava:guava:pom'])
        self.assertTrue('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('2' in al['com.google.guava:guava:pom'])
        self.assertFalse('3' in al['com.google.guava:guava:pom'])
        self.assertFalse('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertFalse('2' in al['org.jboss:jboss-foo:jar'])

        config.multiVersionGAs = ["com.google.guava:guava"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('2' in al['com.google.guava:guava:pom'])
        self.assertTrue('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])
        alf._filterMultipleVersions(al)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('2' in al['com.google.guava:guava:pom'])
        self.assertTrue('3' in al['com.google.guava:guava:pom'])
        self.assertFalse('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertFalse('2' in al['org.jboss:jboss-foo:jar'])

        config.multiVersionGAs = ["*:jboss-foo"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('2' in al['com.google.guava:guava:pom'])
        self.assertTrue('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('2' in al['com.google.guava:guava:pom'])
        self.assertFalse('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])

        config.multiVersionGAs = ["r/.*:jboss-foo/"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('2' in al['com.google.guava:guava:pom'])
        self.assertTrue('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava:pom']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava:pom']['1'])
        self.assertFalse('2' in al['com.google.guava:guava:pom'])
        self.assertFalse('3' in al['com.google.guava:guava:pom'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo:jar']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo:jar'])


if __name__ == '__main__':
    unittest.main()
