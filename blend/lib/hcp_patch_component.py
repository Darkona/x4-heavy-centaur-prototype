import re
import sys

HCP_TURRET_SLOTS = ('01', '02', '04')

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
for n in HCP_TURRET_SLOTS:
    text = re.sub(rf'(<connection name="con_turret_{n}"[^>]*? tags=")[^"]*(")', r'\g<1>combat hittable medium turret hcp_turret\g<2>', text)
    assert f'name="con_turret_{n}"' in text, n
assert 'group_vls' not in text
open(path, 'w', encoding='utf-8').write(text)
print('patched', path)
