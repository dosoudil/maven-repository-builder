import datetime
import hashlib
import copy
import os
import re
from optparse import OptionParser
from xml.dom.minidom import parseString

import maven_repo_util


def _isSnapshot(version):
    return version.endswith("-SNAPSHOT")


def ffilter(parent, dname, art_id):
    if _isSnapshot(dname):
        pomRE = re.compile((re.escape(art_id + "-" + dname + ".pom"))
                  .replace("-SNAPSHOT", "-(SNAPSHOT|\d+\.\d+-\d+)"))
        for filename in os.listdir(os.path.join(parent, dname)):
            if pomRE.match(filename):
                return True
        return False
    else:
        return os.path.exists(os.path.join(parent, dname, art_id + "-" + dname + ".pom"))


parser = OptionParser(usage='%prog [directories]')
(opts, directories) = parser.parse_args()

sorterdir = os.path.dirname(os.path.realpath(__file__)) + '/versionSorter/'

for directory in directories:
    n_dir = os.path.normpath(directory)

    if not os.path.isdir(directory):
        raise Exception("%s is not a directory" % directory)

    group_id = '.'.join(os.path.dirname(n_dir).split('/'))
    art_id = os.path.basename(n_dir)
    versions = [d for d in os.listdir(n_dir) if ffilter(n_dir, d, art_id)]
    versionsReversed = maven_repo_util._sortVersionsWithAtlas(versions, sorterdir)
    versions = copy.deepcopy(versionsReversed)
    versions.reverse()

    latest = versions[-1]
    releaseVersion = None
    for version in versionsReversed:
        if not _isSnapshot(version):
            releaseVersion = version
            break
    last_updated = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    content = "<metadata>"
    content += "<groupId>%s</groupId>" % group_id
    content += "<artifactId>%s</artifactId>" % art_id
    content += "<versioning>"
    content += "<latest>%s</latest>" % latest
    if releaseVersion:
        content += "<release>%s</release>" % releaseVersion
    else:
        content += "<release/>"
    content += "<versions>"
    for version in versions:
        content += "<version>%s</version>" % version
    content += "</versions>"
    content += "<lastUpdated>%s</lastUpdated>" % last_updated
    content += "</versioning>"
    content += "</metadata>"

    ugly_xml = parseString(content).toprettyxml(indent='  ')

    text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    pretty_xml = text_re.sub('>\g<1></', ugly_xml)

    md_file = "%s/maven-metadata.xml" % n_dir

    f = open(md_file, "w")
    f.write(pretty_xml)
    f.close()

    for ext, sum_constr in (('.md5', hashlib.md5()), ('.sha1', hashlib.sha1())):
        sumfile = md_file + ext
        if os.path.exists(sumfile):
            continue
        checksum = maven_repo_util.getChecksum(md_file, sum_constr)
        with open(sumfile, 'w') as sumobj:
            sumobj.write(checksum + '\n')
            sumobj.write(checksum)
