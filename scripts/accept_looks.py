#!/usr/bin/env python3
"""Decide which new looks are good enough to use, and fill in their catalog fields.
Usage: accept_looks.py CODE [CODE ...] [--dry-run]
Runs face_check.py, pose_check.py and object_check.py on looks/previews/CODE.jpg and sets in looks/catalog.json:
  face_match, mouth, banner_y, status ("active" or "retired") and reject_reason.
A look is accepted only if ALL of these hold:
  face cos >= 0.60 (my face)            mouth 0.03-0.12 (slightly open, not closed, not laughing wide)
  pose_check has no WARN (hands sane)    object_check: no phone visible, at most one big person
banner_y: the headline (200 px tall) sits at y150 unless my face starts above y375 in the 1080x1920 video; then it
goes 30 px under my chin. Print-only with --dry-run. Exit 0 always; read the table.
It cannot judge everything (a sixth finger, a warped background): when a human is around, they check the contact sheet.
"""
import json, os, re, subprocess, sys
from PIL import Image
from kit_paths import SCRIPTS as S, LOOKS as D
args = [a for a in sys.argv[1:] if not a.startswith('--')]; dry = '--dry-run' in sys.argv

def run(script, files):
    out = subprocess.run(['python3', os.path.join(S, script)] + files, capture_output=True, text=True).stdout
    return {l.split('\t')[0].replace('.jpg', ''): l for l in out.splitlines() if l.startswith('L')}

files = [os.path.join(D, 'previews', f'{c}.jpg') for c in args]
fc, pc, oc = run('face_check.py', files), run('pose_check.py', files), run('object_check.py', files)
cat = json.load(open(os.path.join(D, 'catalog.json')))
by = {c['code']: c for c in cat}
# Standing rule 4 (after a two-right-hands glitch): strict hand check on the full frame AND on
# close-ups of every hand and of the upper body. Selfie looks may show at most 1 hand, propped looks 2.
hc = {}
for c, f in zip(args, files):
    exp = '2' if by.get(c, {}).get('style') == 'propped' else '1'
    o = subprocess.run(['python3', os.path.join(S, 'hand_check.py'), f, '--expect', exp, '--closeups',
                        os.path.join(D, 'closeups')], capture_output=True, text=True).stdout
    hc[c] = o.strip()
for c, f in zip(args, files):
    why = []
    h = Image.open(f).size[1]
    m = re.search(r'cos=([0-9.]+).*face_y=(\d+)-(\d+)', fc.get(c, ''))
    cos = float(m.group(1)) if m else 0.0
    top, bot = (int(m.group(2)) * 1920 / h, int(m.group(3)) * 1920 / h) if m else (0, 0)
    mm = re.search(r'mouth=([0-9.]+)', pc.get(c, ''))
    mouth = float(mm.group(1)) if mm else 0.0
    if cos < 0.60: why.append(f'face match {cos:.3f} < 0.60')
    if not 0.03 <= mouth <= 0.12: why.append(f'mouth {mouth:.3f} ' + ('closed' if mouth < 0.03 else 'too wide'))
    if 'WARN' in pc.get(c, ''): why.append('hands: ' + pc[c].split('WARN:')[1].strip())
    if 'FLAG' in oc.get(c, ''): why.append(oc[c].split('FLAG:')[1].strip())
    if '\tFAIL' in hc.get(c, ''): why.append('hand_check: ' + hc[c].split('\t')[-1])
    banner = 150 if top >= 375 else int(bot + 30)
    status = 'active' if not why else 'retired'
    print(f"{c}\t{status}\tcos={cos:.3f}\tmouth={mouth:.3f}\tface_y={top:.0f}-{bot:.0f}\tbanner_y={banner}" + (f"\t{'; '.join(why)}" if why else ''))
    if not dry and c in by:
        by[c].update(face_match=round(cos, 3), mouth=round(mouth, 3), banner_y=banner, status=status)
        if why: by[c]['reject_reason'] = '; '.join(why)
        else: by[c].pop('reject_reason', None)
if not dry:
    json.dump(cat, open(os.path.join(D, 'catalog.json'), 'w'), indent=1, ensure_ascii=False)
