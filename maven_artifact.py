
"""maven_artifact.py Python code representing a Maven artifact"""

import logging


class MavenArtifact:

    def __init__(self, groupId, artifactId, artifactType, version, classifier=None):
        self.groupId = groupId
        self.artifactId = artifactId
        self.artifactType = artifactType
        self.version = version
        self.classifier = classifier

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
        return self.getDirPath() + '/' + self.getArtifactFilename()

    def getPomFilename(self):
        """Returns the filename of the pom file for this artifact"""
        return self.getBaseFilename() + '.pom'

    def getPomFilepath(self):
        """Return the path to the artifact file"""
        return self.getDirPath() + '/' + self.getPomFilename()

    def getSourcesFilename(self):
        """Returns the filename of the sources artifact"""
        return self.getBaseFilename() + '-sources.jar'

    def getSourcesFilepath(self):
        """Return the path to the artifact file"""
        return self.getDirPath() + '/' + self.getSourcesFilename()

    def __str__(self):
        result = self.groupId + ':' + self.artifactId + ':' + self.artifactType
        if self.classifier:
            result = result + ':' + self.classifier
        result = result + ':' + self.version
        return result


def createFromGAV(gav):
    """Initialize an artifact using a colon separated
       GAV of the form groupId:artifactId:type:[classifier:]version
    """
    gavParts = gav.split(':')
    if (len(gavParts) >= 4):
        if (len(gavParts) == 4):
            return MavenArtifact(gavParts[0], gavParts[1],
                gavParts[2], gavParts[3])
        elif (len(gavParts) == 5):
            return MavenArtifact(gavParts[0], gavParts[1],
                gavParts[2], gavParts[3], gavParts[4])
    else:
        logging.error('Invalid GAV string: %s', gav)
