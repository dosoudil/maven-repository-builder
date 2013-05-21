import os
import urllib
import urlparse
import shutil


def fetchArtifacts(artifactList, config):
    repoDir = config.resultRepoName
    if not os.path.isdir(repoDir):
        os.mkdir(repoDir)

    for artifact, priorities in artifactList.iteritems():
        for priority, versions in priorities.iteritems():
            for version, fileUrls in versions.iteritems():
                # Create needed directories
                artifactGA = artifact.split(':')
                artifactsDirName = repoDir + '/' + \
                                   artifactGA[0].replace('.', '/') + '/' + \
                                   artifactGA[1] + '/' + \
                                   version
                if not os.path.isdir(artifactsDirName):
                    os.makedirs(artifactsDirName)

                # Download needed files
                for fileUrl in fileUrls:
                    parsedUrl = urlparse.urlparse(fileUrl)
                    protocol = parsedUrl[0]
                    filename = urlparse.urlsplit(fileUrl).path.split("/")[-1]
                    filepath = artifactsDirName + '/' + filename

                    # Download only files that do not exist in the repo dir
                    if filename and not os.path.isfile(filepath):
                        if protocol == 'http' or protocol == 'https':
                            urllib.urlretrieve(fileUrl, filepath)
                        else:
                            shutil.copy2(fileUrl, artifactsDirName)
