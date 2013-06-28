import os
import re
import maven_repo_util
import logging
from multiprocessing.pool import ThreadPool
from subprocess import Popen
from subprocess import PIPE
from subprocess import call
from maven_artifact import MavenArtifact


class ArtifactListBuilder:
    """
    Class loading artifact "list" from sources defined in the given
    configuration. The result is dictionary with following structure:

    "<groupId>:<artifactId>" (string)
      L <artifact source priority> (int)
         L <version> (string)
            L <repo url> (string)
    """

    _fileExtRegExp = "((?:tar\.)?[^.]+)$"

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
                                                       source['included-gav-patterns'])
            elif source['type'] == 'dependency-list':
                logging.info("Building artifact list from top level list of GAVs")
                artifacts = self._listDependencies(source['repo-url'],
                                                   self._parseDepList(source['top-level-gavs']))
            elif source['type'] == 'repository':
                logging.info("Building artifact list from repository %s", source['repo-url'])
                artifacts = self._listRepository(source['repo-url'],
                                                 source['included-gav-patterns'])
            elif source['type'] == 'artifacts':
                logging.info("Building artifact list from list of artifacts")
                artifacts = self._listArtifacts(source['repo-url'],
                                                self._parseDepList(source['included-gavs']))
            else:
                logging.warning("Unsupported source type: %s", source['type'])
                continue

            logging.debug("Placing %d artifacts in the result list", len(artifacts))
            for artifact in artifacts:
                gat = artifact.getGAT()
                artifactList.setdefault(gat, {}).setdefault(priority, {})[artifact.version] = artifacts[artifact]
            logging.debug("The result contains %d GATs so far", len(artifactList))

        return artifactList

    def _listMeadTagArtifacts(self, kojiUrl, downloadRootUrl, tagName, gavPatterns):
        """
        Loads maven artifacts from koji (brew/mead).

        :param kojiUrl: Koji/Brew/Mead URL
        :param downloadRootUrl: Download root URL of the artifacts
        :param tagName: Koji/Brew/Mead tag name
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """
        import koji

        kojiSession = koji.ClientSession(kojiUrl)
        kojiArtifacts = kojiSession.getLatestMavenArchives(tagName)

        gavsWithExts = {}
        for artifact in kojiArtifacts:
            # FIXME: This isn't reliable as file extension is not equal to
            # maven type, e.g. jar != ejb
            artifactType = re.search('.*\.(.+)$', artifact['filename']).group(1)
            gavUrl = maven_repo_util.slashAtTheEnd(downloadRootUrl) + artifact['build_name'] + '/'\
                     + artifact['build_version'] + '/' + artifact['build_release'] + '/maven/'
            gavu = (artifact['group_id'], artifact['artifact_id'], artifact['version'], gavUrl)
            gavsWithExts.setdefault(gavu, []).append(artifactType)

        artifacts = {}
        for gavu in gavsWithExts:
            if len(gavsWithExts[gavu]) > 1:
                gavsWithExts[gavu].remove("pom")
            for ext in gavsWithExts[gavu]:
                mavenArtifact = MavenArtifact(gavu[0], gavu[1], ext, gavu[2])
                artifacts[mavenArtifact] = gavu[3]

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
                pomUrl = maven_repo_util.slashAtTheEnd(repoUrl) + artifact.getPomFilepath()
                fetched = maven_repo_util.fetchFile(pomUrl, pomDir)
                if fetched:
                    break

            if not fetched:
                logging.warning("Failed to retrieve pom file for artifact %s", gav)
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
            with open(mvnOutFilename, "r") as mvnOutFile:
                mvnLines = mvnOutFile.readlines()
            gavList = self._parseDepList(mvnLines)

            artifacts.update(self._listArtifacts(repoUrls, gavList))

        return artifacts

    def _listRepository(self, repoUrls, gavPatterns):
        """
        Loads maven artifacts from a repository.

        :param repoUrl: repository URL (local or remote, supported are [file://], http:// and
                        https:// urls)
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """

        prefixes = self._getPrefixes(gavPatterns)
        artifacts = {}
        for repoUrl in reversed(repoUrls):
            protocol = maven_repo_util.urlProtocol(repoUrl)
            if protocol == 'file':
                for prefix in prefixes:
                    artifacts.update(self._listLocalRepository(repoUrl[7:], prefix))
            elif protocol == '':
                for prefix in prefixes:
                    artifacts.update(self._listLocalRepository(repoUrl, prefix))
            elif protocol == 'http' or protocol == 'https':
                for prefix in prefixes:
                    artifacts.update(self._listRemoteRepository(repoUrl, prefix))
            else:
                raise "Invalid protocol!", protocol

        artifacts = self._filterArtifactsByPatterns(artifacts, gavPatterns)
        logging.debug("Found %d artifacts", len(artifacts))

        return artifacts

    def _getPrefixes(self, gavPatterns):
        repat = re.compile("^r/.*/$")
        patterns = set()
        for pattern in gavPatterns:
            if repat.match(pattern):
                return set([''])
            p = pattern.split(":")
            px = p[0].replace(".", "/") + "/"  # GroupId
            if len(p) >= 2:
                px += p[1] + "/"              # ArtifactId
            if len(p) >= 3:
                px += p[2] + "/"              # Version
            pos = px.find("*")
            if pos == -1:
                patterns.add(px.rpartition("/")[0] + "/")
            else:
                patterns.add(px[:pos].rpartition("/")[0] + "/")
        prefixes = set()
        while patterns:
            pattern = patterns.pop()
            for prefix in patterns | prefixes:
                if pattern.startswith(prefix):
                    break
            else:
                prefixes.add(pattern)
        return prefixes

    def _listRemoteRepository(self, repoUrl, prefix=""):
        logging.debug("Listing remote repository %s prefix '%s'", repoUrl, prefix)
        artifacts = {}
        (out, _) = Popen(r'lftp -c "set ssl:verify-certificate no ; open ' + repoUrl + prefix
                         + ' ; find  ."', stdout=PIPE, shell=True).communicate()

        # ^./(groupId)/(artifactId)/(version)/(filename)$
        regexGAVF = re.compile(r'\./(.+)/([^/]+)/([^/]+)/([^/]+\.[^/.]+)$')
        gavsWithExts = {}
        suffixes = {}
        for line in out.split('\n'):
            if (line):
                line = "./" + prefix + line[2:]
                gavf = regexGAVF.match(line)
                if gavf is not None:
                    av = self._getSnapshotAwareVersionRegEx(re.escape(gavf.group(2) + "-" + gavf.group(3) + "."))
                    regexExt = re.compile(av + self._fileExtRegExp)
                    ext = regexExt.match(gavf.group(4))
                    if ext is not None:
                        gav = (gavf.group(1).replace('/', '.'), gavf.group(2), gavf.group(3))
                        if len(ext.groups()) == 1:
                            gavsWithExts.setdefault(gav, set()).add(ext.group(1))
                        else:
                            gavsWithExts.setdefault(gav, set()).add(ext.group(2))
                            suffix = ext.group(1)
                            if gav not in suffixes or suffixes[gav] < suffix:
                                suffixes[gav] = suffix

        for gav in gavsWithExts:
            exts = gavsWithExts[gav]
            if len(exts) > 1:
                exts.remove("pom")
            for ext in exts:
                mavenArtifact = MavenArtifact(gav[0], gav[1], ext, gav[2])
                if gav in suffixes:
                    mavenArtifact.snapshotVersionSuffix = suffixes[gav]
                artifacts[mavenArtifact] = repoUrl
        return artifacts

    def _listLocalRepository(self, directoryPath, prefix=""):
        """
        Loads maven artifacts from local directory.

        :param directoryPath: Path of the local directory.
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL
                  starting with 'file://'.
        """
        logging.debug("Listing local repository %s prefix '%s'", directoryPath, prefix)
        artifacts = {}
        # ^(groupId)/(artifactId)/(version)$
        regexGAV = re.compile(r'^(.*)/([^/]*)/([^/]*)$')
        for dirname, dirnames, filenames in os.walk(directoryPath + prefix, followlinks=True):
            if filenames:
                logging.debug("Looking for artifacts in %s", dirname)
                gavPath = dirname.replace(directoryPath, '')
                gav = regexGAV.search(gavPath)
                av = self._getSnapshotAwareVersionRegEx(re.escape(gav.group(2) + "-" + gav.group(3) + "."))
                regexExt = re.compile(av + self._fileExtRegExp)
                exts = set()
                suffix = None
                for filename in filenames:
                    ext = regexExt.match(filename)

                    if ext is not None:
                        if len(ext.groups()) == 1:
                            exts.add(ext.group(1))
                        else:
                            exts.add(ext.group(2))
                            if suffix is None or suffix < ext.group(1):
                                suffix = ext.group(1)

                if len(exts) > 1 and "pom" in exts:
                    exts.remove("pom")
                for ext in exts:
                    # Remove first slash if present then convert to GroupId
                    groupId = re.sub("^/", "", gav.group(1)).replace('/', '.')
                    mavenArtifact = MavenArtifact(groupId, gav.group(2), ext, gav.group(3))
                    if suffix is not None:
                        mavenArtifact.snapshotVersionSuffix = suffix
                    logging.debug("Adding artifact %s", str(mavenArtifact))
                    artifacts[mavenArtifact] = "file://" + directoryPath
        return artifacts

    def _getSnapshotAwareVersionRegEx(self, version):
        """Prepares the version string to be part of regular expression for filename and when the
        version is a snapshot version, it corrects the suffix to match even when the files are
        named with the timestamp and build number as usual in case of snapshot versions."""
        return version.replace("-SNAPSHOT", "-(SNAPSHOT|\d+\.\d+-\d+)")

    def _listArtifacts(self, urls, gavs):
        """
        Loads maven artifacts from list of GAVs and tries to locate the artifacts in one of the
        specified repositories.

        :param urls: repository URLs where the given GAVs can be located
        :param gavs: List of GAVs
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """
        def findArtifact(gav, urls, artifacts):
            artifact = MavenArtifact.createFromGAV(gav)
            for url in urls:
                if maven_repo_util.gavExists(url, artifact):
                    #Critical section?
                    artifacts[artifact] = url
                    return

            logging.warning('artifact %s not found in any url!', artifact)

        artifacts = {}
        pool = ThreadPool(maven_repo_util.MAX_THREADS)
        for gav in gavs:
            pool.apply_async(findArtifact, [gav, urls, artifacts])

        # Close the pool and wait for the workers to finnish
        pool.close()
        pool.join()

        return artifacts

    def _parseDepList(self, depList):
        """Parse maven dependency:list output and return a list of GAVs"""
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

    def _filterArtifactsByPatterns(self, artifacts, gavPatterns):
        if not gavPatterns:
            return artifacts

        regExps = maven_repo_util.getRegExpsFromStrings(gavPatterns)
        includedArtifacts = {}
        for artifact in artifacts:
            if maven_repo_util.somethingMatch(regExps, artifact.getGAV()):
                includedArtifacts[artifact] = artifacts[artifact]
        return includedArtifacts
