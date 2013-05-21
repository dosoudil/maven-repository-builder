import urlparse
import os
import koji
import re
from subprocess import Popen
from subprocess import PIPE
from subprocess import call
from xml.etree import ElementTree
from maven_artifact import MavenArtifact


class ArtifactListBuilder:
    """
    Class loading artifact "list" from sources defined in the given
    configuration. The result is dictionary with following structure:

    "<groupId>:<artifactId>" (string)
      L <artifact source priority> (int)
         L <version> (string)
            L <file url> (list of strings)
    """

    def __init__(self, configuration):
        self.configuration = configuration

    def buildList(self):
        """
        Build the artifact "list" from sources defined in the given configuration.
        """
        artifactList = {}
        priority = 0
        for source in self.configuration.artifactSources:
            priority += 1

            if source['type'] == 'mead-tag':
                artifacts = self._listMeadTagArtifacts(source['koji-url'], source['download-root-url'], source['tag-name'])
            elif source['type'] == 'dependency-list':
                artifacts = self._listDependencies(source['git-url'], source['module'], source['repo-urls'])
            elif source['type'] == 'nexus-repository':
                artifacts = self._listNexusRepository(source['nexus-url'], source['repo-name'])
            elif source['type'] == 'local-repository':
                artifacts = self._listDirectoryArtifacts(source['root-dir'])
            elif source['type'] == 'artifacts':
                artifacts = self._listArtifacts(source['repo-urls'], source['included-gavs'])
            else:
                print "Unsupported source type: ", source['type']

            for artifact in artifacts:
                ga = artifact.getGA()

                if not ga in artifactList:
                    artifactList[ga] = {}
                if not priority in artifactList[ga]:
                    artifactList[ga][priority] = {}

                artifactList[ga][priority][artifact.version] = self._getFiles(artifacts[artifact])

        return artifactList


    def _listMeadTagArtifacts(self, kojiUrl, downloadRootUrl, tagName):
        """
        Loads maven artifacts from koji (brew/mead).
        Returns dictionary where index is MavenArtifact object and value is the artifact URL.
        """

        kojiSession = koji.ClientSession(kojiUrl)
        kojiArtifacts = kojiSession.getLatestMavenArchives(tagName)

        artifacts = {}
        for artifact in kojiArtifacts:
            mavenArtifact = MavenArtifact(artifact['group_id'], artifact['artifact_id'],
                            artifact['version'])

            gavUrl = self._slashAtTheEnd(downloadRootUrl) + artifact['build_name'] + '/'\
                    + artifact['build_version'] + '/' + artifact['build_release']\
                    + '/maven/' +  artifact['group_id'].replace('.', '/') + '/'\
                    +  artifact['artifact_id'] + '/' +  artifact['version'] + '/'
            artifacts[mavenArtifact] = gavUrl

        return artifacts


    def _listDependencies(self, gitUrl, moduleName, repoUrls):
        """
        Loads maven artifacts from mvn dependency:list.
        Returns dictionary where index is MavenArtifact object and value is the artifact URL.
        """

        repoName = self._parseRepoName(gitUrl)
        repoPath = 'repos/' + repoName + '/'

        # Clone Git Repository
        call(['git', 'clone', gitUrl, repoPath])

        # Build dependency:list
        mvnOutFile = "mvn-output-" + repoName + ".log"
        with open(mvnOutFile, "w") as mvnOutput:
            command = ['mvn', 'dependency:list', '-f']
            if moduleName:
                call(['mvn', 'install', '-f', repoPath + 'pom.xml'])
                call(command + [repoPath + moduleName + '/pom.xml'], stdout=mvnOutput)
            else:
                call(command + [repoPath + 'pom.xml'], stdout=mvnOutput)

        # Parse GAVs from maven output
        with open(mvnOutFile, "r") as mvnOutput:
            depListLines = mvnOutput.readlines()
            gavList = self._parseDepList(depListLines)

        return self._listArtifacts(repoUrls, gavList)


    def _listNexusRepository(self, nexusUrl, repoName):
        """
        Loads maven artifacts from nexus repository.
        Returns dictionary where index is MavenArtifact object and value is the artifact URL.
        """
        nexusBase = self._slashAtTheEnd(nexusUrl)
        repoUrl = nexusBase + 'content/repositories/' + repoName + '/'
        artifacts = {}
        for index in range(ord('a'), ord('z')):
            qUrl = nexusBase + "service/local/lucene/search?q=" + chr(index) + "*&repositoryId=" + repoName
            xmlResult = urllib.urlopen(qUrl).read()
            et = ElementTree.fromstring(xmlResult)
            data = et.find('data')
            for artifact in data.findall("artifact"):
                mavenArtifact = MavenArtifact(artifact.find('groupId').text, artifact.find('artifactId').text,
                                artifact.find('version').text)

                gavUrl = repoUrl + mavenArtifact.groupId.replace('.', '/') + '/'\
                        +  mavenArtifact.artifactId + '/' +  mavenArtifact.version + '/'
                artifacts[mavenArtifact] = gavUrl

        return artifacts


    def _listDirectoryArtifacts(self, directoryPath):
        """
        Loads maven artifacts from local directory.
        Returns dictionary where index is MavenArtifact object and value is the artifact URL starting with 'file://'.
        """
        artifacts = {}
        regexGAV = re.compile(r'(^.*)/([^/]*)/([^/]*$)')
        for dirname, dirnames, filenames in os.walk(directoryPath):
            if not dirnames:
                gavPath = dirname.replace(directoryPath, '')
                gav = regexGAV.search(gavPath)
                mavenArtifact = MavenArtifact(gav.group(1).replace('/', '.'), gav.group(2),
                                            gav.group(3))
                artifacts[mavenArtifact] = 'file://' + dirname

        return artifacts

    def _listArtifacts(self, urls, gavs):
        """
        Loads maven artifacts from list of GAVs and tries to locate the artifacts in one of the specified repositories.
        Returns dictionary where index is MavenArtifact object and value is the artifact URL.
        """
        artifacts = {}
        for gav in gavs:
            artifact = MavenArtifact.createFromGAV(gav)
            for url in urls:
                gavUrl = url + artifact.getDirPath()
                if self._gavExistsInUrl(gavUrl):
                    artifacts[artifact] = gavUrl
                    break
            if not artifact in artifacts:
                print 'artifact ' + artifact.__str__() + ' not found in any url!'

        return artifacts


    def _getFiles(self, gavUrl):
        parsedUrl = urlparse.urlparse(gavUrl)
        protocol = parsedUrl[0]
        if protocol == 'http' or protocol == 'https':
            return self._remoteFind(gavUrl)
        elif protocol == 'file':
            return self._localFind(gavUrl)
        else:
            print 'Unknown protocol: ', protocol

    def _localFind(self, gavUrl):
        files = []
        gavPath = gavUrl.replace('file://', '')
        for dirname, dirnames, filenames in os.walk(gavPath):
            for filename in filenames:
                files.append('file://' + os.path.join(gavPath, dirname, filename))
        return files

    def _remoteFind(self, gavUrl):
        files = []
        (out,_) = Popen(r'lftp -c "set ssl:verify-certificate no ; open ' + gavUrl + ' ; find "', stdout = PIPE, shell = True).communicate()
        for line in out.split('\n'):
            if line == '': continue
            files.append(gavUrl + line)
        return files

    def _gavExistsInUrl(self, gavUrl):
        parsedUrl = urlparse.urlparse(gavUrl)
        protocol = parsedUrl[0]
        if protocol == 'http' or protocol == 'https':
            return urllib.urlopen(gavUrl).getcode() == 200
        else:
            return os.path.exists(gavUrl)

    def _slashAtTheEnd(self, url):
        if url.endswith('/'):
            return url
        else:
            return url + '/'

    def _parseDepList(self, depList):
        """Parse maven dependency:list output and return a list of GAVs"""
        regexComment = re.compile('#.*$')
        # Match pattern groupId:artifactId:type:[classifier:]version[:scope]
        regexGAV = re.compile('(([\w\-.]+:){3}([\w\-.]+:)?([\d][\w\-.]+))(:[\w]*\S)?')
        gavList = []
        for nextLine in depList:
            nextLine = regexComment.sub('', nextLine)
            nextLine = nextLine.strip()
            gav = regexGAV.search(nextLine)
            if gav:
                gavList.append(gav.group(1))
        return gavList

    def _parseRepoName(self, repoUrl):
        """Parse repository name from the URL"""
        repoName = re.search('[/:]([^/]+)/{0,1}$', repoUrl)
        print repoUrl
        if repoName:
            return repoName.group(1)
        else:
            return None
