JBoss EAP Maven Repository
==========================

This archive contains Maven repository artifacts for JBoss EAP 6.  This is meant
to be used in a development environment for JBoss EAP 6 applications.


Installation (Option 1) - Local File System
--------------------------------

For initial testing in a small team, the repository can be extracted to 
a directory on the local file system.

    unzip jboss-eap-6.1.X-maven-repository.zip

This will create a Maven repository in a directory called "jboss-eap-6.0-maven-repository".
Make a note of the location of this directory for later use.

 
Installation (Option 2) - Apache Web Server
--------------------------------
 
To use the repository in a multi-user environment, the repository can be installed 
in a standard webserver such as Apache httpd, or a Maven repository manager such as Nexus.
To install the repository in Apache, simply unzip the repository in a web accessible 
directory on the Apache server.

    unzip jboss-eap-6.1.X-maven-repository.zip

This will create a Maven repository in a directory called "jboss-eap-6.0-maven-repository".
Apache should then be configured to allow read access and directory browsing in this directory.

 
Installation (Option 3) - Maven Repository Manager
--------------------------------------------------

If you already use a repository manager, you can use it to host the  EAP  repository alongside 
your existing repositories.  Please refer to the documentation for your repository manager,
for example:

* [Apache Archiva](http://archiva.apache.org/)
* [JFrog Artifactory](http://www.jfrog.com/products.php)
* [Sonatype Nexus](http://nexus.sonatype.org/)
 
Maven Configuration
-------------------

In order to correctly use this repository, the Maven settings (settings.xml) will 
need to be updated.  A default settings.xml file is included with each Maven distribution 
in the "conf" directory.  The Maven user settings is normally found in the ".m2" sub-directory 
of the user's home directory.  For more information about configuring Maven, refer to the 
[Maven site](http://maven.apache.org/settings.html).

The URL of the repository will depend on where the 
repository is located (i.e. on the filesystem, web server etc).  A few example 
URLs are provided here:

* File system - file:///path/to/repo/jboss-eap-6.1.X-maven-repository
* Apache Web Server - http://intranet.acme.com/jboss-eap-6.1.X-maven-repository
* Nexus Repository Manager - https://intranet.acme.com/nexus/content/repositories/jboss-eap-6.1.X-maven-repository

An example Maven settings file (example-settings.xml) is included in the root directory of the Maven
repository zip file.  An excerpt containing the relevant portions of settings.xml is provided below.
More information about configuring your Maven  settings is available on the Apache Maven site.

 
    <settings>
      ...
      <profiles>
        ...
        <profile>
          <id>jboss-eap-repository</id>
          <repositories>
            <repository>
              <id>jboss-eap-repository</id>
              <name>JBoss EAP Maven Repository</name>
              <url>file:///path/to/repo/jboss-eap-6.1.X-maven-repository</url>
              <layout>default</layout>
              <releases>
                <enabled>true</enabled>
                <updatePolicy>never</updatePolicy>
              </releases>
              <snapshots>
                <enabled>false</enabled>
                <updatePolicy>never</updatePolicy>
              </snapshots>
            </repository>
          </repositories>
          <pluginRepositories>
            <pluginRepository>
              <id>jboss-eap-repository-group</id>
              <name>JBoss EAP Maven Repository</name>
              <url>file:///path/to/repo/jboss-eap-6.1.X-maven-repository</url>
              <layout>default</layout>
              <releases>
                <enabled>true</enabled>
                <updatePolicy>never</updatePolicy>
              </releases>
              <snapshots>
                <enabled>false</enabled>
                <updatePolicy>never</updatePolicy>
              </snapshots>
            </pluginRepository>
          </pluginRepositories>
        </profile>

      </profiles>

      <activeProfiles>
        <activeProfile>jboss-eap-repository</activeProfile>
      </activeProfiles>
      ...
    </settings>

 
Project Configuration
---------------------

For more detailed project examples please see the JBoss EAP quickstarts documentation.

