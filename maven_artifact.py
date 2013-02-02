# Python code representing a Maven artifact

class MavenArtifact:

    def __init__(self, gav):
        """Initialize an artifact using a colon separated GAV to relative path groupId:artifactId:type:version"""
        gavParts = gav.split(':')
        self.groupId = gavParts[0]
        self.artifactId = gavParts[1]
        self.artifactType = gavParts[2]
        self.version = gavParts[3]


    def getRelativePath(self):
        """Get the relative repository path to the artifact"""
        relativePath = self.groupId.replace('.', '/') + '/'
        relativePath += self.artifactId + '/'
        relativePath += self.version + '/'
        return relativePath


    def getBaseFilename(self):
        """Returns the filename without the file extension"""
        filename = self.artifactId + '-' + self.version 
        return filename


    def getArtifactFilename(self):
        """Returns the filename of the artifact"""
        return self.getBaseFilename() + '.' + self.artifactType


    def getPomFilename(self):
        """Returns the filename of the pom file for this artifact"""
        return self.getBaseFilename() + '.pom'  


    def getSourcesFilename(self):
        """Returns the filename of the sources artifact"""
        return self.getBaseFilename() + '-sources.jar'

