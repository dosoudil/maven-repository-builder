
"""maven_artifact.py Python code representing a Maven artifact"""

import logging
import sys


class MavenArtifact:

    def __init__(self, groupId, artifactId, artifactType, version, classifier=''):
        self.groupId = groupId
        self.artifactId = artifactId
        self.artifactType = artifactType
        self.version = version
        self.classifier = classifier

    @staticmethod
    def createFromGAV(gav):
        """
        Initialize an artifact using a colon separated
        GAV of the form groupId:artifactId:[type:][classifier:]version[:scope]

        :returns: MavenArtifact instance
        """
        gavParts = gav.split(':')
        if len(gavParts) not in [3, 4, 5, 6]:
            logging.error("Invalid GAV string: %s", gav)
            sys.exit(1)
        groupId = gavParts[0]
        artifactId = gavParts[1]

        scopes = ["compile", "test", "provided", "runtime", "system"]
        if gavParts[-1] in scopes:
            effectiveParts = len(gavParts) - 1
        else:
            effectiveParts = len(gavParts)

        artifactType = ''
        classifier = ''
        if effectiveParts == 3:
            version = gavParts[2]
        else:
            artifactType = gavParts[2]
            if effectiveParts == 4:
                version = gavParts[3]
            else:
                classifier = gavParts[3]
                version = gavParts[4]

        return MavenArtifact(groupId, artifactId, artifactType, version, classifier)

    def getArtifactType(self):
        return self.artifactType

    def getClassifier(self):
        return self.classifier

    def getDirPath(self):
        """Get the relative repository path to the artifact"""
        relativePath = self.groupId.replace('.', '/') + '/'
        relativePath += self.artifactId + '/'
        relativePath += self.version + '/'
        return relativePath

    def getGA(self):
        """Get the groupId and artifactId using a colon separated form."""
        return self.groupId + ":" + self.artifactId

    def getGAT(self):
        """Get the groupId, artifactId and artifact type using a colon separated form."""
        return self.groupId + ":" + self.artifactId + ":" + self.artifactType

    def getGAV(self):
        """Get the groupId, artifactId and version using a colon separated form."""
        return self.groupId + ":" + self.artifactId + ":" + self.version

    def getBaseFilename(self):
        """Returns the filename without the file extension"""
        baseFilename = self.artifactId + '-' + self.version
        return baseFilename

    def getArtifactFilename(self):
        """Returns the filename of the artifact"""
        filename = self.getBaseFilename()
        if (self.classifier):
            filename += '-' + self.classifier
        return filename + '.' + self.artifactType

    def getArtifactFilepath(self):
        """Return the path to the artifact file"""
        return self.getDirPath() + self.getArtifactFilename()

    def getPomFilename(self):
        """Returns the filename of the pom file for this artifact"""
        return self.getBaseFilename() + '.pom'

    def getPomFilepath(self):
        """Return the path to the artifact file"""
        return self.getDirPath() + self.getPomFilename()

    def getSourcesFilename(self):
        """Returns the filename of the sources artifact"""
        return self.getBaseFilename() + '-sources.jar'

    def getSourcesFilepath(self):
        """Return the path to the artifact file"""
        return self.getDirPath() + self.getSourcesFilename()

    def __str__(self):
        result = self.groupId + ':' + self.artifactId
        if self.artifactType:
            result += ':' + self.artifactType
        result += ':' + self.version
        return result
