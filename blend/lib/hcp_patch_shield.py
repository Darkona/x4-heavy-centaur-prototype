import re
import sys
import xml.etree.ElementTree as ET

NAME = 'con_shield_l_01'
TAGS = 'large shield hcp_shield'
POSITION = (0, -10, -45)

path = sys.argv[1]
text = open(path, encoding='utf-8').read()
if 'name="%s"' % NAME in text:
    print('internal shield already present')
    sys.exit(0)
block = ('      <connection name="%s" tags="%s">\n'
         '        <offset>\n'
         '          <position x="%s" y="%s" z="%s" />\n'
         '        </offset>\n'
         '      </connection>\n') % ((NAME, TAGS) + POSITION)
anchor = re.search(r'\n(\s*)<connection name="con_shipstorage_s_01"', text)
if not anchor:
    anchor = re.search(r'\n(\s*)<connection name="space"', text)
text = text[:anchor.start() + 1] + block + text[anchor.start() + 1:]
ET.fromstring(text.encode('utf-8'))
open(path, 'w', encoding='utf-8').write(text)
print('patched internal shield', NAME)
