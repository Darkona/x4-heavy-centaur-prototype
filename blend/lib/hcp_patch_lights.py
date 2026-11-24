import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

path = sys.argv[1]
text = open(path, encoding='utf-8').read()
if '<waypoints>' not in text:
    waypoints = (Path(__file__).with_name('hcp_waypoints.xml')).read_text(encoding='utf-8')
    if '<layer />' in text:
        text = text.replace('<layer />', '<layer>\n' + waypoints + '</layer>', 1)
    else:
        text = text.replace('<layer>', '<layer>\n' + waypoints, 1)
    print('patched waypoints')
def light_xml(d):
    attrs = {'name': d['name']}
    attrs.update(d['attrs'])
    head = ' '.join('%s="%s"' % (k, v) for k, v in attrs.items())
    body = []
    if d.get('size'):
        body.append('<size x="%s" y="%s" z="%s" />' % tuple(d['size']))
    if d.get('anim'):
        keys = ''.join('<key frame="%d" value="%s" />' % (f, v) for f, v in d['anim'])
        body.append('<lightanimations><lightanimation name="intensity" controller="linear_float">%s</lightanimation></lightanimations>' % keys)
    else:
        body.append('<lightanimations />')
    off = '<position x="%s" y="%s" z="%s" />' % tuple(d['position'])
    if d.get('quat'):
        off += '<quaternion qx="%s" qy="%s" qz="%s" qw="%s" />' % tuple(d['quat'])
    body.append('<offset>%s</offset>' % off)
    return '<%s %s>\n  %s\n</%s>' % (d['kind'], head, '\n  '.join(body), d['kind'])


lights = json.loads(Path(__file__).with_name('hcp_lights.json').read_text(encoding='utf-8'))
block = ''.join(light_xml(d) + '\n' for d in lights if 'name="%s"' % d['name'] not in text)
if block:
    if '<layer />' in text:
        text = text.replace('<layer />', '<layer><lights>' + block + '</lights></layer>', 1)
    elif '<lights>' in text:
        text = text.replace('<lights>', '<lights>' + block, 1)
    elif '<lights />' in text:
        text = text.replace('<lights />', '<lights>' + block + '</lights>', 1)
    else:
        text = text.replace('<layer>', '<layer><lights>' + block + '</lights>', 1)
ET.fromstring(text.encode('utf-8'))
open(path, 'w', encoding='utf-8').write(text)
print('lights in component', text.count('<omni ') + text.count('<box ') + text.count('<spot '), 'added', block.count('<omni ') + block.count('<box ') + block.count('<spot '))
