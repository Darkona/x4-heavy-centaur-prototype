#!/bin/bash
set -e
W=$(cd "$(dirname "$0")/../.." && pwd)
L=$W/blend/lib
X=~/development/x4
EB="$X/p1[assets]/extensions/heavy_centaur_prototype/assets/units/size_l/ship_arg_l_hcp_01.blend"
export WINEPREFIX=~/.local/share/wineprefixes/egosoft WINEDEBUG=-all
echo "[1] build"; cd $W/blend && blender -b hcp_work.blend --python lib/hcp_build_export.py 2>&1 | tail -2
echo "[2] vhacd"; cd $L/vhacd && rm -f part_main[0-9]*.obj && wine ~/Documents/Egosoft/Tools/VHACD.exe part_main.obj -h 128 -v 32 -r 1000000 -a true -o obj >/dev/null 2>&1; ls part_main[0-9]*.obj | wc -l
echo "[3] hulls"; blender -b "$EB" --python $L/hcp_add_hulls.py 2>&1 | tail -2
echo "[4] clip"; blender -b "$EB" --python $L/hcp_clip_hulls.py 2>&1 | grep -iE "inside|hulls|error" | tail -3
echo "[5] export"; cd $X && wine "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe" -b "Z:\\home\\darkona\\development\\x4\\p1[assets]\\extensions\\heavy_centaur_prototype\\assets\\units\\size_l\\ship_arg_l_hcp_01.blend" --python "Z:\\home\\darkona\\development\\x4\\hcp-integracion\\blend\\lib\\hcp_export.py" >/dev/null 2>&1; rm -f "${EB}1"
echo "[6] convert"; touch ${TMPDIR:-/tmp}/xuc.mark; sleep 1
cd $X && (wine "C:\\Program Files\\EGOSOFT\\Egosoft Blender Mod Tools\\Converter\\XUConverter.exe" 'Z:\home\darkona\development\x4\p1[assets]' 'Z:\home\darkona\development\x4\p1data' >/dev/null 2>&1 & echo $! > ${TMPDIR:-/tmp}/xuc.pid)
for i in $(seq 1 180); do f=$(find $X -maxdepth 2 -name XUConverterLog.txt -newer ${TMPDIR:-/tmp}/xuc.mark 2>/dev/null | head -1); [ -n "$f" ] && grep -q "Processed:" "$f" && break; sleep 2; done
grep -h "Processed:" $(find $X -maxdepth 2 -name XUConverterLog.txt) | tail -1
kill $(cat ${TMPDIR:-/tmp}/xuc.pid) 2>/dev/null || true
echo "[7] copy+patch"; SRC=$X/p1data/extensions/heavy_centaur_prototype/assets/units/size_l; DST=$W/mod/heavy_centaur_prototype/assets/units/size_l
rm -rf $DST/ship_arg_l_hcp_01_data; cp -r $SRC/ship_arg_l_hcp_01_data $DST/; find $DST/ship_arg_l_hcp_01_data -name '*.dae' -delete; cp $SRC/ship_arg_l_hcp_01.xml $SRC/ship_arg_l_hcp_01_data.ani $DST/
for p in lights component shield; do python3 $L/hcp_patch_$p.py $DST/ship_arg_l_hcp_01.xml | tail -1; done
grep -c "<connection name" $DST/ship_arg_l_hcp_01.xml
echo DONE
