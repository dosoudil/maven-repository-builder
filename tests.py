#!/usr/bin/env python

""" tests.py: Unit tests for maven repo builder and related tools"""

import logging
import os
import tempfile
import unittest
import copy

import artifact_list_builder
import configuration
import maven_repo_util
from aprox_apis import AproxApi10
from artifact_list_builder import ArtifactListBuilder, ArtifactSpec, ArtifactType
from maven_repo_util import ChecksumMode
from maven_artifact import MavenArtifact
from configuration import Configuration
from filter import Filter


class Tests(unittest.TestCase):

    artifactList = {
      "com.google.guava:guava": {
        "1": {
          "1.0.0": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("pom", True, set(['']))]),
          "1.0.1": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("pom", True, set(['']))]),
          "1.1.0": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("pom", True, set(['']))])},
        "2": {
          "1.0.2": ArtifactSpec("http://repo2.maven.org/maven2/", [ArtifactType("pom", True, set(['']))])},
        "3": {
          "1.2.0": ArtifactSpec("http://repo3.maven.org/maven2/", [ArtifactType("pom", True, set(['']))]),
          "1.0.0": ArtifactSpec("http://repo3.maven.org/maven2/", [ArtifactType("pom", True, set(['']))])}},
      "org.jboss:jboss-foo": {
        "1": {
          "1.0.0": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("jar", True, set(['']))]),
          "1.0.1": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("jar", True, set(['']))]),
          "1.1.0": ArtifactSpec("http://repo1.maven.org/maven2/", [ArtifactType("jar", True, set(['']))])},
        "2": {
          "1.0.1": ArtifactSpec("http://repo2.maven.org/maven2/", [ArtifactType("jar", True, set(['']))]),
          "1.0.2": ArtifactSpec("http://repo2.maven.org/maven2/", [ArtifactType("jar", True, set(['']))])}}}

    def setUp(self):
        logging.basicConfig(format="%(levelname)s (%(threadName)s): %(message)s", level=logging.DEBUG)

    def test_url_download(self):
        # make sure the shuffled sequence does not lose any elements
        url = "http://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.pom"
        tempDownloadDir = tempfile.mkdtemp()
        filepath = os.path.join(tempDownloadDir, "downloadfile.txt")
        self.assertFalse(os.path.exists(filepath), "Download file already exists: " + filepath)
        maven_repo_util.download(url, filepath, ChecksumMode.generate)
        self.assertTrue(os.path.exists(filepath), "File not downloaded")

        maven_repo_util.download(url, None, ChecksumMode.generate)
        localfilename = "jboss-parent-10.pom"
        self.assertTrue(os.path.exists(localfilename))
        if os.path.exists(localfilename):
            logging.debug('Removing temp local file: ' + localfilename)
            os.remove(localfilename)

    def test_bad_urls(self):
        url = "junk://repo1.maven.org/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_util.download(url, None, ChecksumMode.generate)

        url = "sadjfasfjsl"
        maven_repo_util.download(url, None, ChecksumMode.generate)

        url = "http://1234/maven2/org/jboss/jboss-parent/10/jboss-parent-10.p"
        maven_repo_util.download(url, None, ChecksumMode.generate)

    def test_http_404(self):
        url = "http://repo1.maven.org/maven2/somefilethatdoesnotexist"
        code = maven_repo_util.download(url, None, ChecksumMode.generate)
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
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        alf._filterExcludedGAVs(al)
        self.assertFalse('1.1.0' in al['com.google.guava:guava']['1'])

        config.excludedGAVs = ["com.google.guava:guava:1.0*"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.2' in al['com.google.guava:guava']['2'])
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['3'])
        alf._filterExcludedGAVs(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertFalse('2' in al['com.google.guava:guava'])
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['3'])

        config.excludedGAVs = ["com.google.guava:*"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('com.google.guava:guava' in al)
        alf._filterExcludedGAVs(al)
        self.assertFalse('com.google.guava:guava' in al)

    def test_filter_excludedTypes(self):
        config = Configuration()
        alf = Filter(config)

        config.excludedTypes = ["zip", "war"]
        al = copy.deepcopy(self.artifactList)
        al["foo:bar"] = {
          "1": {
            "1.0.0": ArtifactSpec("http://repo1.maven.org/maven2/",
                                  [ArtifactType("zip", True, set([''])), ArtifactType("pom", False, set(['']))])
          }
        }
        
        alf._filterExcludedTypes(al)
        self.assertFalse('foo:bar' in al)

        al["foo:bar"] = {
          "1": {
            "1.0.0": ArtifactSpec("http://repo1.maven.org/maven2/",
                                  [ArtifactType("zip", True, set([''])), ArtifactType("pom", False, set(['']))])
          }
        }
        config.gatcvWhitelist = ["*:zip:scm-sources:*"]
        alf._filterExcludedTypes(al)
        self.assertFalse('foo:bar' in al)

        al["foo:bar"] = {
          "1": {
            "1.0.0": ArtifactSpec("http://repo1.maven.org/maven2/",
                                  [ArtifactType("zip", True, set(['scm-sources'])),
                                   ArtifactType("pom", False, set(['']))])
          }
        }
        alf._filterExcludedTypes(al)
        self.assertTrue('foo:bar' in al)

    def test_filter_duplicates(self):
        config = Configuration()
        alf = Filter(config)

        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['3'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['2'])
        alf._filterDuplicates(al)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['3'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo']['2'])

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
        o = set([""])
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

        i = ["org.abc.def:qwer:1.0.1", "org.abc.def:qwer:1.2.1",
             "r/(org|com).*/"]
        o = set([""])
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

        i = []
        o = set([""])
        out = alb._getPrefixes(i)
        self.assertEqual(out, o)

    def test_filter_multiple_versions(self):
        config = Configuration()
        config.singleVersion = True
        alf = Filter(config)

        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('2' in al['com.google.guava:guava'])
        self.assertTrue('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('2' in al['com.google.guava:guava'])
        self.assertFalse('3' in al['com.google.guava:guava'])
        self.assertFalse('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertFalse('2' in al['org.jboss:jboss-foo'])

        config.multiVersionGAs = ["com.google.guava:guava"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('2' in al['com.google.guava:guava'])
        self.assertTrue('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])
        alf._filterMultipleVersions(al)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('2' in al['com.google.guava:guava'])
        self.assertTrue('3' in al['com.google.guava:guava'])
        self.assertFalse('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertFalse('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertFalse('2' in al['org.jboss:jboss-foo'])

        config.multiVersionGAs = ["*:jboss-foo"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('2' in al['com.google.guava:guava'])
        self.assertTrue('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('2' in al['com.google.guava:guava'])
        self.assertFalse('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])

        config.multiVersionGAs = ["r/.*:jboss-foo/"]
        al = copy.deepcopy(self.artifactList)
        self.assertTrue('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertTrue('2' in al['com.google.guava:guava'])
        self.assertTrue('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])
        alf._filterMultipleVersions(al)
        self.assertFalse('1.0.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('1.0.1' in al['com.google.guava:guava']['1'])
        self.assertTrue('1.1.0' in al['com.google.guava:guava']['1'])
        self.assertFalse('2' in al['com.google.guava:guava'])
        self.assertFalse('3' in al['com.google.guava:guava'])
        self.assertTrue('1.0.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.0.1' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('1.1.0' in al['org.jboss:jboss-foo']['1'])
        self.assertTrue('2' in al['org.jboss:jboss-foo'])

    def _getExpectedArtifacts(self, repoUrl, dependencies):

        artSpecDict = {}
        for dep in dependencies.keys():
            artifact = MavenArtifact.createFromGAV(dep)
            artTypes = []
            artTypes.append(ArtifactType(artifact.artifactType, artifact.artifactType != "pom", dependencies[dep]))
            artSpec = ArtifactSpec(repoUrl, artTypes)
            gav = artifact.getGAV()
            if gav in artSpecDict.keys():
                artSpecDict[gav].merge(artSpec)
            else:
                artSpecDict[gav] = artSpec
        expectedArtifacts = {}
        for (gav, artSpec) in artSpecDict.iteritems():
            artifact = MavenArtifact.createFromGAV(gav)
            expectedArtifacts[artifact] = artSpec

        return expectedArtifacts

    def test_listDependencies(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        repoUrls = ['http://repo.maven.apache.org/maven2/']
        gavs = [
            'com.sun.faces:jsf-api:2.0.11',
            'org.apache.ant:ant:1.8.0'
        ]
        dependencies = {
            'javax.servlet:javax.servlet-api:pom:3.0.1': set(['']),
            'javax.servlet:javax.servlet-api:jar:3.0.1': set(['', 'javadoc', 'sources']),
            'javax.servlet.jsp.jstl:jstl-api:pom:1.2': set(['']),
            'javax.servlet.jsp.jstl:jstl-api:jar:1.2': set(['', 'javadoc', 'sources']),
            'xml-apis:xml-apis:pom:1.3.04': set(['']),
            'xml-apis:xml-apis:jar:1.3.04': set(['', 'source', 'sources']),
            'javax.servlet:servlet-api:pom:2.5': set(['']),
            'javax.servlet:servlet-api:jar:2.5': set(['', 'sources']),
            'javax.el:javax.el-api:pom:2.2.1': set(['']),
            'javax.el:javax.el-api:jar:2.2.1': set(['', 'javadoc', 'sources']),
            'junit:junit:pom:3.8.2': set(['']),
            'junit:junit:jar:3.8.2': set(['', 'javadoc', 'sources']),
            'xerces:xercesImpl:pom:2.9.0': set(['']),
            'xerces:xercesImpl:jar:2.9.0': set(['']),
            'javax.servlet.jsp:jsp-api:pom:2.1': set(['']),
            'javax.servlet.jsp:jsp-api:jar:2.1': set(['', 'sources']),
            'javax.servlet.jsp:javax.servlet.jsp-api:pom:2.2.1': set(['']),
            'javax.servlet.jsp:javax.servlet.jsp-api:jar:2.2.1': set(['', 'javadoc', 'sources']),
            'org.apache.ant:ant-launcher:pom:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:jar:1.8.0': set([''])
        }
        expectedArtifacts = self._getExpectedArtifacts(repoUrls[0], dependencies)

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listDependencies(repoUrls, gavs, False, False)

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listDependencies_recursive(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        repoUrls = ['http://repo.maven.apache.org/maven2/']
        gavs = [
            'com.sun.faces:jsf-api:2.0.11',
            'org.apache.ant:ant:1.8.0'
        ]
        dependencies = {
            'junit:junit:pom:3.8.2': set(['']),
            'junit:junit:jar:3.8.2': set(['', 'sources', 'javadoc']),
            'xerces:xercesImpl:pom:2.9.0': set(['']),
            'xerces:xercesImpl:jar:2.9.0': set(['']),
            'xml-apis:xml-apis:pom:1.3.04': set(['']),
            'xml-apis:xml-apis:jar:1.3.04': set(['', 'source', 'sources']),
            'javax.el:javax.el-api:pom:2.2.1': set(['']),
            'javax.el:javax.el-api:jar:2.2.1': set(['', 'sources', 'javadoc']),
            'xml-resolver:xml-resolver:pom:1.2': set(['']),
            'xml-resolver:xml-resolver:jar:1.2': set(['', 'sources']),
            'javax.servlet:servlet-api:pom:2.5': set(['']),
            'javax.servlet:servlet-api:jar:2.5': set(['', 'sources']),
            'javax.servlet.jsp:jsp-api:pom:2.1': set(['']),
            'javax.servlet.jsp:jsp-api:jar:2.1': set(['', 'sources']),
            'org.apache.ant:ant-launcher:pom:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:jar:1.8.0': set(['']),
            'javax.servlet.jsp.jstl:jstl-api:pom:1.2': set(['']),
            'javax.servlet.jsp.jstl:jstl-api:jar:1.2': set(['', 'sources', 'javadoc']),
            'javax.servlet:javax.servlet-api:pom:3.0.1': set(['']),
            'javax.servlet:javax.servlet-api:jar:3.0.1': set(['', 'sources', 'javadoc']),
            'javax.servlet.jsp:javax.servlet.jsp-api:pom:2.2.1': set(['']),
            'javax.servlet.jsp:javax.servlet.jsp-api:jar:2.2.1': set(['', 'sources', 'javadoc'])
        }
        expectedArtifacts = self._getExpectedArtifacts(repoUrls[0], dependencies)

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listDependencies(repoUrls, gavs, True, False)

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listDependencyGraph_allclassifiers(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        aproxUrl = 'http://aprox-dev.app.eng.bos.redhat.com:8080/aprox/'
        sourceKey = "repository:central"
        topGavs = [
            'org.apache.ant:ant:1.8.0'
        ]
        dependencies = {
            'org.apache.ant:ant:pom:1.8.0': set(['']),
            'org.apache.ant:ant:jar:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:pom:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:jar:1.8.0': set(['']),
            'org.apache.ant:ant-parent:pom:1.8.0': set(['']),
            'org.apache:apache:pom:3': set(['']),
            'org.apache:apache:pom:4': set(['']),
            'xerces:xercesImpl:pom:2.9.0': set(['']),
            'xerces:xercesImpl:jar:2.9.0': set(['']),
            'xml-apis:xml-apis:pom:1.3.04': set(['']),
            'xml-apis:xml-apis:jar:1.3.04': set(['', 'source', 'sources']),
            'xml-resolver:xml-resolver:pom:1.2': set(['']),
            'xml-resolver:xml-resolver:jar:1.2': set(['', 'sources'])
        }
        expectedArtifacts = self._getExpectedArtifacts(aproxUrl, dependencies)

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listDependencyGraph(aproxUrl, None, sourceKey, topGavs)

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listDependencyGraph_specified_classifiers(self):
        config = configuration.Configuration()
        config.addClassifiers = config._parseClassifiers("sources,dummy")
        aproxUrl = 'http://aprox-dev.app.eng.bos.redhat.com:8080/aprox/'
        sourceKey = "repository:central"
        topGavs = [
            'org.apache.ant:ant:1.8.0'
        ]
        dependencies = {
            'org.apache.ant:ant:pom:1.8.0': set(['']),
            #'org.apache.ant:ant:jar:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:pom:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:jar:1.8.0': set(['']),
            'org.apache.ant:ant-parent:pom:1.8.0': set(['']),
            'org.apache:apache:pom:3': set(['']),
            'org.apache:apache:pom:4': set(['']),
            'xerces:xercesImpl:pom:2.9.0': set(['']),
            'xerces:xercesImpl:jar:2.9.0': set(['']),
            'xml-apis:xml-apis:pom:1.3.04': set(['']),
            'xml-apis:xml-apis:jar:1.3.04': set(['', 'sources']),
            'xml-resolver:xml-resolver:pom:1.2': set(['']),
            'xml-resolver:xml-resolver:jar:1.2': set(['', 'sources'])
        }
        expectedArtifacts = self._getExpectedArtifacts(aproxUrl, dependencies)

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listDependencyGraph(aproxUrl, None, sourceKey, topGavs)

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listDependencyGraph(self):
        config = configuration.Configuration()
        config.addClassifiers = ""
        aproxUrl = 'http://aprox-dev.app.eng.bos.redhat.com:8080/aprox/'
        sourceKey = "repository:central"
        topGavs = [
            'org.apache.ant:ant:1.8.0'
        ]
        dependencies = {
            'org.apache.ant:ant:pom:1.8.0': set(['']),
            #'org.apache.ant:ant:jar:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:pom:1.8.0': set(['']),
            'org.apache.ant:ant-launcher:jar:1.8.0': set(['']),
            'org.apache.ant:ant-parent:pom:1.8.0': set(['']),
            'org.apache:apache:pom:3': set(['']),
            'org.apache:apache:pom:4': set(['']),
            'xerces:xercesImpl:pom:2.9.0': set(['']),
            'xerces:xercesImpl:jar:2.9.0': set(['']),
            'xml-apis:xml-apis:pom:1.3.04': set(['']),
            'xml-apis:xml-apis:jar:1.3.04': set(['']),
            'xml-resolver:xml-resolver:pom:1.2': set(['']),
            'xml-resolver:xml-resolver:jar:1.2': set([''])
        }
        expectedArtifacts = self._getExpectedArtifacts(aproxUrl, dependencies)

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listDependencyGraph(aproxUrl, None, sourceKey, topGavs)

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_aproxCreateDeleteWorkspace(self):
        aproxUrl = 'http://aprox-dev.app.eng.bos.redhat.com:8080/aprox/'
        aproxApi = AproxApi10(aproxUrl)

        ws = aproxApi.createWorkspace()
        wsid = ws["id"]

        delResult = aproxApi.deleteWorkspace(wsid)

        self.assertTrue(delResult)

    def test_listMeadTagArtifacts(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        kojiUrl = "http://brewhub.devel.redhat.com/brewhub/"
        tagName = "mead-import-maven"
        downloadRootUrl = "http://download.devel.redhat.com/brewroot/packages/"
        gavPatts = [
            'org.apache.maven:maven-core:2.0.6'
        ]

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listMeadTagArtifacts(kojiUrl, downloadRootUrl, tagName, gavPatts)
        expectedUrl = downloadRootUrl + "org.apache.maven-maven-core/2.0.6/1/maven/"
        expectedArtifacts = {
            MavenArtifact.createFromGAV(gavPatts[0]): ArtifactSpec(expectedUrl, [
                    ArtifactType("pom", True, set([''])),
                    ArtifactType("jar", True, set(['', 'javadoc', 'sources']))])
        }

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listRepository_http(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        repoUrls = ['http://repo.maven.apache.org/maven2/']
        gavPatts = [
            'com.sun.faces:jsf-api:2.0.11',
            'org.apache.ant:ant:1.8.0'
        ]

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listRepository(repoUrls, gavPatts)
        expectedArtifacts = {
            MavenArtifact.createFromGAV(gavPatts[0]): ArtifactSpec(repoUrls[0], [ArtifactType("pom", True, set([''])),
                                        ArtifactType("jar", True, set(['', 'javadoc', 'sources']))]),
            MavenArtifact.createFromGAV(gavPatts[1]): ArtifactSpec(repoUrls[0], [ArtifactType("pom", True, set([''])),
                                        ArtifactType("jar", True, set(['']))])
        }

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_listRepository_file(self):
        config = configuration.Configuration()
        config.addClassifiers = "__all__"
        repoUrls = ['file://./tests/testrepo']
        gavPatts = [
            'bar:foo-bar:1.1',
            'foo.baz:baz-core:1.0'
        ]

        builder = artifact_list_builder.ArtifactListBuilder(config)
        actualArtifacts = builder._listRepository(repoUrls, gavPatts)
        expectedArtifacts = {
            MavenArtifact.createFromGAV(gavPatts[0]): ArtifactSpec(repoUrls[0], [ArtifactType("pom", True, set(['']))]),
            MavenArtifact.createFromGAV(gavPatts[1]): ArtifactSpec(repoUrls[0], [ArtifactType("pom", True, set([''])),
                                        ArtifactType("jar", True, set(['', 'javadoc', 'sources']))])
        }

        self.assertEqualArtifactList(expectedArtifacts, actualArtifacts)

    def test_parseClassifiers(self):
        config = Configuration()
        classifiers = config._parseClassifiers("sources")
        expectedClassifiers = [{"classifier": "sources", "type": "jar"}]
        self.assertEquals(expectedClassifiers, classifiers)

        classifiers = config._parseClassifiers("jar:sources")
        expectedClassifiers = [{"classifier": "sources", "type": "jar"}]
        self.assertEquals(expectedClassifiers, classifiers)

        classifiers = config._parseClassifiers("sources,javadoc,zip:scm-sources")
        expectedClassifiers = [{"classifier": "sources", "type": "jar"}, {"classifier": "javadoc", "type": "jar"},
                               {"classifier": "scm-sources", "type": "zip"}]
        self.assertEquals(expectedClassifiers, classifiers)

    def assertEqualArtifactList(self, expectedArtifacts, actualArtifacts):
        strExp = self._artifactListToString(expectedArtifacts, "  expected", "\n    ")
        strAct = self._artifactListToString(actualArtifacts, "  actual", "\n    ")

        logging.debug("Comparing artifact lists:\n%s\n%s", strExp, strAct)

        # Assert that length of expectedArtifacts is the same as of actualArtifacts
        self.assertEqual(len(expectedArtifacts), len(actualArtifacts))

        # Assert that artifact list contains all dependencies with correct classifiers
        for expectedArtifact in expectedArtifacts:
            foundArtifact = None
            for actualArtifact in actualArtifacts:
                if actualArtifact.getGAV() == expectedArtifact.getGAV():
                    foundArtifact = actualArtifact
            self.assertTrue(foundArtifact is not None)

            logging.debug("Checking types of %s", expectedArtifact)
            self.assertEquals(expectedArtifacts[expectedArtifact].artTypes.keys(),
                              actualArtifacts[foundArtifact].artTypes.keys())

            for artType in actualArtifacts[foundArtifact].artTypes:
                foundClassifiers = actualArtifacts[foundArtifact].artTypes[artType].classifiers
                expectedType = expectedArtifacts[expectedArtifact].artTypes[artType]
                expectedClassifiers = expectedType.classifiers
                logging.debug("Checking found classifiers (%s, expected are %s) of %s:%s:%s", foundClassifiers,
                              expectedClassifiers, foundArtifact.getGA(), artType, foundArtifact.version)
                self.assertEquals(expectedClassifiers, foundClassifiers)

    def _artifactListToString(self, artifactList, listName, separator):
        strList = []
        for artifact in artifactList:
            strList.append(str(artifact))
        strList.sort()
        strList.insert(0, listName + ":")
        return separator.join(strList)


if __name__ == '__main__':
    unittest.main()
