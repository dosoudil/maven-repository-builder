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
            L artifact specification (repo url string and list of found classifiers)
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
                                                       source['included-gav-patterns'])
            elif source['type'] == 'dependency-list':
                logging.info("Building artifact list from top level list of GAVs")
                artifacts = self._listDependencies(source['repo-url'],
                                                   self._parseDepList(source['top-level-gavs']))
            elif source['type'] == 'repository':
                logging.info("Building artifact list from repository %s", source['repo-url'])
                artifacts = self._listRepository(source['repo-url'],
                                                 source['included-gav-patterns'])
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

        gavuExtClass = {} # { (g,a,v,url): {ext: set([class])} }
        suffixes = {} # { (g,a,v,url): suffix }
        for artifact in kojiArtifacts:
            groupId = artifact['group_id']
            artifactId = artifact['artifact_id']
            version = artifact['version']
            filename = artifact['filename']

            (extsAndClass, suffix) = self._getExtensionsAndClassifiers(artifactId, version, [filename])

            if extsAndClass:
                gavUrl = maven_repo_util.slashAtTheEnd(downloadRootUrl) + artifact['build_name'] + '/'\
                         + artifact['build_version'] + '/' + artifact['build_release'] + '/maven/'
                gavu = (groupId, artifactId, version, gavUrl)

                gavuExtClass.setdefault(gavu, {})
                self._updateExtensionsAndClassifiers(gavuExtClass[gavu], extsAndClass)

                if suffix is not None and (gavu not in suffixes or suffixes[gavu] < suffix):
                    suffixes[gavu] = suffix

        artifacts = {}
        for gavu in gavuExtClass:
            self._addArtifact(artifacts, gavu[0], gavu[1], gavu[2], gavuExtClass[gavu], suffixes.get(gavu), gavu[3])

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
        :param gavPatterns: list of patterns to filter by GAV
        :returns: Dictionary where index is MavenArtifact object and value is it's repo root URL.
        """

        prefixes = self._getPrefixes(gavPatterns)
        artifacts = {}
        for repoUrl in reversed(repoUrls):
            urlWithSlash = maven_repo_util.slashAtTheEnd(repoUrl)
            protocol = maven_repo_util.urlProtocol(urlWithSlash)
            if protocol == 'file':
                for prefix in prefixes:
                    artifacts.update(self._listLocalRepository(urlWithSlash[7:], prefix))
            elif protocol == '':
                for prefix in prefixes:
                    artifacts.update(self._listLocalRepository(urlWithSlash, prefix))
            elif protocol == 'http' or protocol == 'https':
                for prefix in prefixes:
                    artifacts.update(self._listRemoteRepository(urlWithSlash, prefix))
            else:
                raise "Invalid protocol!", protocol

        artifacts = self._filterArtifactsByPatterns(artifacts, gavPatterns)
        logging.debug("Found %d artifacts", len(artifacts))

        return artifacts

    def _getPrefixes(self, gavPatterns):
        if not gavPatterns:
            return set([''])
        repat = re.compile("^r/.*/$")
        prefixrepat = re.compile("^(([a-zA-Z0-9-]+|\\\.|:)+)")
        patterns = set()
        for pattern in gavPatterns:
            if repat.match(pattern):  # if pattern is regular expresion pattern "r/expr/"
                kp = prefixrepat.match(pattern[2:-1])
                if kp:
                    # if the expr starts with readable part (eg. "r/org\.jboss:core-.*:.*/")
                    # convert readable part to asterisk string: "org.jboss:*"
                    pattern = kp.group(1).replace("\\", "") + "*"
                else:
                    return set([''])
            p = pattern.split(":")
            px = p[0].replace(".", "/") + "/"  # GroupId
            if len(p) >= 2:
                px += p[1] + "/"               # ArtifactId
            if len(p) >= 3:
                px += p[2] + "/"               # Version
            pos = px.find("*")
            if pos != -1:
                px = px[:pos]
            partitions = px.rpartition("/")
            if partitions[0]:
                patterns.add(partitions[0] + "/")
            else:
                # in case there is no slash before the first star
                return set([''])

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
        (out, _) = Popen(r'lftp -c "set ssl:verify-certificate no ; open ' + repoUrl + prefix
                         + ' ; find  ."', stdout=PIPE, shell=True).communicate()

        # ^./(groupId)/(artifactId)/(version)/(filename)$
        regexGAVF = re.compile(r'\./(.+)/([^/]+)/([^/]+)/([^/]+\.[^/.]+)$')
        gavExtClass = {} # { (g,a,v): {ext: set([class])} }
        suffixes = {} # { (g,a,v): suffix }
        for line in out.split('\n'):
            if (line):
                line = "./" + prefix + line[2:]
                gavf = regexGAVF.match(line)
                if gavf is not None:
                    groupId = gavf.group(1).replace('/', '.')
                    artifactId = gavf.group(2)
                    version = gavf.group(3)
                    filename = gavf.group(4)

                    (extsAndClass, suffix) = self._getExtensionsAndClassifiers(artifactId, version, [filename])

                    gav = (groupId, artifactId, version)

                    gavExtClass.setdefault(gav, {})
                    self._updateExtensionsAndClassifiers(gavExtClass[gav], extsAndClass)

                    if suffix is not None and (gav not in suffixes or suffixes[gav] < suffix):
                        suffixes[gav] = suffix

        artifacts = {}
        for gav in gavExtClass:
            self._addArtifact(artifacts, gav[0], gav[1], gav[2], gavExtClass[gav], suffixes.get(gav), repoUrl)
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
        # ^(groupId)/(artifactId)/(version)/?$
        regexGAV = re.compile(r'^(.+)/([^/]+)/([^/]+)/?$')
        for dirname, dirnames, filenames in os.walk(directoryPath + prefix, followlinks=True):
            if filenames:
                logging.debug("Looking for artifacts in %s", dirname)
                gavPath = dirname.replace(directoryPath, '')
                gav = regexGAV.search(gavPath)
                #If gavPath is e.g. example/sth, then gav is None
                if not gav:
                    continue

                # Remove first slash if present then convert to GroupId
                groupId = re.sub("^/", "", gav.group(1)).replace('/', '.')
                artifactId = gav.group(2)
                version = gav.group(3)

                (extsAndClass, suffix) = self._getExtensionsAndClassifiers(artifactId, version, filenames)

                url = "file://" + directoryPath
                self._addArtifact(artifacts, groupId, artifactId, version, extsAndClass, suffix, url)

        return artifacts

    def _getExtensionsAndClassifiers(self, artifactId, version, filenames):
        # returns ({ext: set([classifier])}, suffix)
        av = self._getArtifactVersionREString(artifactId, version)
        # artifactId-(version)-(classifier).(extension)
        #                          (classifier)       (   extension   )
        ceRegEx = re.compile(av + "(?:-([^.]+))\." + "((?:tar\.)?[^.]+)$")

        suffix = None
        extensions = {}
        for filename in filenames:
            ce = ceRegEx.match(filename)
            if ce:
                realVersion = ce.group(1)
                classifier = ce.group(2)
                ext = ce.group(3)

                extensions.setdefault(ext, set())
                if classifier is not None:
                    extensions[ext].add(classifier)

                if realVersion != version:
                    if suffix is None or suffix < realVersion:
                        suffix = realVersion
        return (extensions, suffix)

    def _addArtifact(self, artifacts, groupId, artifactId, version, extsAndClass, suffix, url):
        if extsAndClass > 1 and "pom" in extsAndClass:
            del extsAndClass["pom"]
        for ext in extsAndClass:
            mavenArtifact = MavenArtifact(groupId, artifactId, ext, version)
            if suffix is not None:
                mavenArtifact.snapshotVersionSuffix = suffix
            logging.debug("Adding artifact %s", str(mavenArtifact))
            artifacts[mavenArtifact] = ArtifactSpec(url, extsAndClass[ext])

    def _updateExtensionsAndClassifiers(self, d, u):
        for extension, classifiers in u.iteritems():
            d.setdefault(extension, set()).update(classifiers)

    def _getArtifactVersionREString(self, artifactId, version):
        if version == "SNAPSHOT":
            # """Prepares the version string to be part of regular expression for filename and when the
            # version is a snapshot version, it corrects the suffix to match even when the files are
            # named with the timestamp and build number as usual in case of snapshot versions."""
            versionPattern = r'(SNAPSHOT|\d+\.\d+-\d+)'
        else:
            versionPattern = "(" + re.escape(version) + ")"
        return re.escape(artifactId) + "-" + versionPattern

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
                    artifacts[artifact] = ArtifactSpec(url)
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


class ArtifactSpec:
    """Specification of artifact location and contents."""

    def __init__(self, url, classifiers=[]):
        self.url = url
        self.classifiers = classifiers

    def __str__(self):
        return self.url + " " + str(self.classifiers)
