import json
import math
import os
import re
import sys

POINTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hcp_turret_points.json')


def normalized(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def quaternion(x, y, z):
    m = [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    if m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        return (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    if m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        return ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
    return ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)


def turret_offset(point):
    y = normalized(point['axis_out_x4'])
    zj = point['z_axis_x4']
    d = sum(a * b for a, b in zip(zj, y))
    z = normalized([-(c - d * a) for c, a in zip(zj, y)])
    q = quaternion(cross(y, z), y, z)
    pos = ' '.join(f'{a}="{v:.6g}"' for a, v in zip('xyz', point['centre_x4']))
    quat = ' '.join(f'{a}="{v:.7g}"' for a, v in zip(('qx', 'qy', 'qz', 'qw'), q))
    return f'<offset>\n          <position {pos} />\n          <quaternion {quat} />\n        </offset>'


path = sys.argv[1]
text = open(path, encoding='utf-8').read()

space_old = '<connection name="space" tags="ship_m ship" />'
space_new = '<connection name="space" tags="ship_l ship" />'
if space_new not in text:
    assert text.count(space_old) == 1, space_old
    text = text.replace(space_old, space_new)

if 'con_weapon_vls_01' not in text:
    for n in ('01', '02'):
        old = f'<connection name="con_turret_vls_{n}" group="group_vls " tags="combat hittable medium missile turret  hcp_vls" hidden="true">'
        assert text.count(old) == 1, old
        text = text.replace(old, f'<connection name="con_turret_vls_{n}" tags="nocollision part hcp_vls_hatchmount" hidden="true">')
    anchor = '      <connection name="con_weapon_missile_01"'
    assert text.count(anchor) == 1
    slots = ''
    for n, side, pos in (('01', 'left', 'x="0" y="-4.765" z="10"'), ('02', 'right', 'x="0" y="-2.782" z="30"')):
        slots += (f'      <connection name="con_weapon_vls_{n}" tags="medium missile weapon hcp_vls symmetry symmetry_top symmetry_{side} symmetry_5 ">\n'
                  f'        <offset>\n          <position {pos} />\n        </offset>\n      </connection>\n')
    text = text.replace(anchor, slots + anchor)
points = json.load(open(POINTS, encoding='utf-8'))
for slot, point in sorted(points.items()):
    n = slot.split('_')[-1]
    text, k = re.subn(rf'(<connection name="con_turret_{n}"[^>]*? tags=")[^"]*(")', r'\g<1>combat hittable medium turret hcp_turret\g<2>', text)
    assert k == 1, n
    text, k = re.subn(rf'(<connection name="con_turret_{n}"[^>]*>\s*)<offset>.*?</offset>', lambda m: m.group(1) + turret_offset(point), text, flags=re.S)
    assert k == 1, n
assert 'group_vls' not in text
open(path, 'w', encoding='utf-8').write(text)
print('patched', path)
