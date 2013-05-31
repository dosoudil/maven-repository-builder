
"""maven_artifact.py Python code representing a Maven artifact"""

import logging

class MavenArtifact:

    def __init__(self, gav):
        """Initialize an artifact using a colon separated 
           GAV of the form groupId:artifactId:type:[classifier:]version
        """
        gavParts = gav.split(':')
        if (len(gavParts) >= 4):
            self.groupId = gavParts[0]
            self.artifactId = gavParts[1]
            self.artifactType = gavParts[2]
            if (len(gavParts) == 4):
                self.classifier = ''
                self.version = gavParts[3]
            elif (len(gavParts) == 5):
                self.classifier = gavParts[3]
                self.version = gavParts[4]
        else: 
            logging.error('Invalid GAV string: %s', gav)

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

