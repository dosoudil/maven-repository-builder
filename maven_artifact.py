
class MavenArtifact:

    # Initialize an artifact using a colon separated GAV to relative path groupId:artifactId:type:version
    def __init__(self, gav):
        gavParts = gav.split(':')
        self.groupId = gavParts[0]
        self.artifactId = gavParts[1]
        self.artifactType = gavParts[2]
        self.version = gavParts[3]

    def getRelativePath(self):
        relativePath = self.groupId.replace('.', '/') + '/'
        relativePath += self.artifactId + '/'
        relativePath += self.version + '/'
        return relativePath

    # Returns the filename of the artifact
    def getArtifactFilename(self):
        filename = self.artifactId + '-' + self.version + '.' + self.artifactType
        return filename

    # Returns the filename without the file extension
    def getBaseFilename(self):
        filename = self.artifactId + '-' + self.version 
        return filename
  

