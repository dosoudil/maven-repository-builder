import os
import koji
import re
import mrbutils
import logging
from subprocess import Popen
from subprocess import PIPE
from subprocess import call
from maven_artifact import MavenArtifact
from download import fetchArtifact


class ArtifactListBuilder:
    """
    Class loading artifact "list" from sources defined in the given
    configuration. The result is dictionary with following structure:

    "<groupId>:<artifactId>" (string)
      L <artifact source priority> (int)
         L <version> (string)
            L <repo url> (string)
    """

    def __init__(self, configuration):
        self.configuration = configuration

    def buildList(self):
        """
        Build the artifact "list" from sources defined in the given configuration.

        :returns: Dictionary descirebed above.
        """
        artifactList = {}
        priority = 0
        for source in self.configuration.artifactSources:
            priority += 1

            if source['type'] == 'mead-tag':
                logging.info("Building artifact list from tag %s", source['tag-name'])
                artifacts = self._listMeadTagArtifacts(source['koji-url'],
                                                       source['download-root-url'],
                                                       source['tag-name'],
                                                       self._readLines(source['included-gav-patterns-ref']))
            elif source['type'] == 'dependency-list':
                logging.info("Building artifact list from top level list of GAVs")
                artifacts = self._listDependencies(source['repo-url'],
                                                   self._parseDepList(source['top-level-gavs-ref']))
            elif source['type'] == 'repository':
                logging.info("Building artifact list from repository %s", source['repo-url'])
                artifacts = self._listRepository(source['repo-url'],
                                                 self._readLines(source['included-gav-patterns-ref']))
            elif source['type'] == 'artifacts':
                logging.info("Building artifact list from list of artifacts")
                artifacts = self._listArtifacts(source['repo-url'],
                                                self._parseDepList(source['included-gavs-ref']))
            else:
                logging.warning("Unsupported source type: %s", source['type'])
                continue

            for artifact in artifacts:
                ga = artifact.getGA()

                if not ga in artifactList:
                    artifactList[ga] = {}
                if not priority in artifactList[ga]:
                    artifactList[ga][priority] = {}

                artifactList[ga][priority][artifact.version] = artifacts[artifact]

        return artifactList

    def _listMeadTagArtifacts(self, kojiUrl, downloadRootUrl, tagName, gavPatterns):
        """
        Loads maven artifacts from koji (brew/mead).

        :param kojiUrl: Koji/Brew/Mead URL
        :param downloadRootUrl: Download root URL of the artifacts
        :param tagName: Koji/Brew/Mead tag name
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """

        kojiSession = koji.ClientSession(kojiUrl)
        kojiArtifacts = kojiSession.getLatestMavenArchives(tagName)

        artifacts = {}
        for artifact in kojiArtifacts:
            # FIXME: This isn't reliable as file extension is not equal to
            # maven type, e.g. jar != ejb
            artifactType = re.search('.*\.(.+)$', artifact['filename']).group(1)
            mavenArtifact = MavenArtifact(artifact['group_id'], artifact['artifact_id'],
                                          artifactType, artifact['version'])

            gavUrl = mrbutils.slashAtTheEnd(downloadRootUrl) + artifact['build_name'] + '/'\
                     + artifact['build_version'] + '/' + artifact['build_release'] + '/maven/'
            artifacts[mavenArtifact] = gavUrl

        return self._filterArtifactsByPatterns(artifacts, gavPatterns)

    def _listDependencies(self, repoUrls, gavs):
        """
        Loads maven artifacts from mvn dependency:list.

        :param repoUrls: URL of the repositories that contains the listed artifacts
        :param gavs: List of top level GAVs
        :returns: Dictionary where index is MavenArtifact object and value is
                  it's repo root URL, or empty dictionary if something goes wrong.
        """
        artifacts = {}

        for gav in gavs:
            artifact = MavenArtifact.createFromGAV(gav)

            pomDir = 'poms'
            fetched = False
            for repoUrl in repoUrls:
                pomUrl = repoUrl + '/' + artifact.getPomFilepath()
                if fetchArtifact(pomUrl, pomDir):
                    fetched = True
                    break

            if not fetched:
                logging.warning("Failed to retrieve pom file for artifact %s",
                                gav)
                continue

            # Build dependency:list
            mvnOutDir = "maven"
            if not os.path.isdir(mvnOutDir):
                os.makedirs(mvnOutDir)
            mvnOutFilename = mvnOutDir + "/" + artifact.getBaseFilename() + "-maven.out"
            with open(mvnOutFilename, "w") as mvnOutputFile:
                retCode = call(['mvn', 'dependency:list', '-N', '-f',
                                pomDir + '/' + artifact.getPomFilename()], stdout=mvnOutputFile)

                if retCode != 0:
                    logging.warning("Maven failed to finish with success. Skipping artifact %s",
                                    gav)
                    continue

            # Parse GAVs from maven output
            gavList = self._parseDepList(mvnOutFilename)

            artifacts.update(self._listArtifacts(repoUrls, gavList))

        return artifacts

    def _listRepository(self, repoUrls, gavPatterns):
        """
        Loads maven artifacts from a repository.

        :param repoUrl: repository URL (local or remote, supported are [file://], http:// and
                        https:// urls)
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """
        artifacts = {}
        for repoUrl in repoUrls:
            protocol = mrbutils.urlProtocol(repoUrl)
            if protocol == 'file':
                artifacts = self._listLocalRepository(repoUrl[7:])
            elif protocol == '':
                artifacts = self._listLocalRepository(repoUrl)
            elif protocol == 'http' or protocol == 'https':
                artifacts = self._listRemoteRepository(repoUrl)
            else:
                raise "Invalid protocol!", protocol

        return self._filterArtifactsByPatterns(artifacts, gavPatterns)

    def _listRemoteRepository(self, repoUrl):
        artifacts = {}
        (out, _) = Popen(r'lftp -c "set ssl:verify-certificate no ; open ' + repoUrl
                         + ' ; find " | egrep "^\./.*/[0-9].*/$"', stdout=PIPE, shell=True)\
                         .communicate()

        regexGAV = re.compile(r'\./(.*)/([^/]*)/([^/]*)/$')

        for line in out.split('\n'):
            if (line):
                print line
                gav = regexGAV.search(line)
                mavenArtifact = MavenArtifact(gav.group(1).replace('/', '.'), gav.group(2),
                                            gav.group(3))

                gavUrl = repoUrl + mavenArtifact.groupId.replace('.', '/') + '/'\
                        + mavenArtifact.artifactId + '/' + mavenArtifact.version + '/'
                artifacts[mavenArtifact] = gavUrl
        return artifacts

    def _listLocalRepository(self, directoryPath):
        """
        Loads maven artifacts from local directory.

        :param directoryPath: Path of the local directory.
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL
                  starting with 'file://'.
        """
        repoRoot = mrbutils.slashAtTheEnd(directoryPath)
        artifacts = {}
        regexGAV = re.compile(r'(^.*)/([^/]*)/([^/]*$)')
        for dirname, dirnames, filenames in os.walk(directoryPath):
            if not dirnames:
                artifactTypes = []
                extRegexp = re.compile('.*\.([^.]+)$')
                for filename in filenames:
                    extension = extRegexp.search(filename)
                    # Could be a file without extension
                    if extension:
                        artifactType = extension.group(1)
                    else:
                        artifactType = filename

                    if artifactType in ['repositories','lastUpdated','sha1','pom']: continue
                    artifactTypes.append(artifactType)
                if not artifactTypes:
                    artifactTypes.append('pom')
                gavPath = dirname.replace(directoryPath, '')
                gav = regexGAV.search(gavPath)
                for artifactType in artifactTypes:
                    groupId = gav.group(1).replace('/', '.')
                    if groupId.startswith("."):
                        groupId = groupId.replace(".", "", 1)
                    mavenArtifact = MavenArtifact(groupId, gav.group(2),
                                                  artifactType, gav.group(3))
                    artifacts[mavenArtifact] = "file://" + directoryPath

        return artifacts

    def _listArtifacts(self, urls, gavs):
        """
        Loads maven artifacts from list of GAVs and tries to locate the artifacts in one of the
        specified repositories.

        :param urls: repository URLs where the given GAVs can be located
        :param gavs: List of GAVs
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """
        artifacts = {}
        for gav in gavs:
            artifact = MavenArtifact.createFromGAV(gav)
            for url in urls:
                gavUrl = url + '/' + artifact.getDirPath()
                if mrbutils.urlExists(gavUrl):
                    artifacts[artifact] = url
                    break
            if not artifact in artifacts:
                logging.warning('artifact %s not found in any url!', artifact)

        return artifacts

    def _parseDepList(self, depListFilename):
        """Parse maven dependency:list output and return a list of GAVs"""
        depList = self._readLines(depListFilename)

        regexComment = re.compile('#.*$')
        # Match pattern groupId:artifactId:[type:][classifier:]version[:scope]
        regexGAV = re.compile('(([\w\-.]+:){2,3}([\w\-.]+:)?([\d][\w\-.]+))(:[\w]*\S)?')
        gavList = []
        for nextLine in depList:
            nextLine = regexComment.sub('', nextLine)
            nextLine = nextLine.strip()
            gav = regexGAV.search(nextLine)
            if gav:
                gavList.append(gav.group(1))

        return gavList

    def _readLines(self, filepath):
        if filepath:
            with open(filepath, "r") as file:
                return file.readlines()

    def _filterArtifactsByPatterns(self, artifacts, gavPatterns):
        if not gavPatterns:
            return artifacts

        includedArtifacts = {}
        for artifact in artifacts:
            matches = map(lambda x: re.match(x, artifact.getGAV()), gavPatterns)
            if any(matches):
                includedArtifacts[artifact] = artifacts[artifact]
        return includedArtifacts
