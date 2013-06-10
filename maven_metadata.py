from xml.dom.minidom import parseString
import datetime
from optparse import OptionParser
from pkg_resources import parse_version
import os
import re

def ffilter(parent, dname, art_id):
  return os.path.exists(os.path.join(parent, dname, art_id + "-" + dname + ".pom"))

def version_comparator(x, y):
  return cmp(parse_version(x), parse_version(y))

parser = OptionParser(usage='%prog [directories]')
(opts, directories) = parser.parse_args()

for directory in directories:
  n_dir = os.path.normpath(directory)
  
  if not os.path.isdir(directory):
    raise Exception("%s is not a directory" % directory)

  group_id = '.'.join(os.path.dirname(n_dir).split('/'))
  art_id = os.path.basename(n_dir)
  versions = [d for d in os.listdir(n_dir) if ffilter(n_dir, d, art_id)]
  versions = sorted(versions, cmp=version_comparator)
  version = versions[-1]
  last_updated = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

  content =  "<metadata>"
  content += "<groupId>%s</groupId>" % group_id
  content += "<artifactId>%s</artifactId>" % art_id
  content += "<versioning>"
  content += "<latest>%s</latest>" % version
  content += "<release>%s</release>" % version
  content += "<versions>"
  for v in versions:
    content += "<version>%s</version>" % v
  content += "</versions>"
  content += "<lastUpdated>%s</lastUpdated>" % last_updated
  content += "</versioning>"
  content += "</metadata>"

  ugly_xml = parseString(content).toprettyxml(indent='  ')

  text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)    
  pretty_xml = text_re.sub('>\g<1></', ugly_xml)

  md_file = "%s/maven-metadata.xml" % n_dir

  f = open(md_file, "w")
  f.write (pretty_xml)
  f.close()
