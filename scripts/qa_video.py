#!/usr/bin/env python3
"""STANDING RULE 1: analyse every video before posting it.
Pre-post check of a render or a finished video. Free tools only (MediaPipe, OpenCV, FFmpeg). No HeyGen.

Usage:
  qa_video.py VIDEO.mp4 [--every 0.2] [--from S --to S]... [--sheet OUT.jpg] [--json OUT.json] [--expect-hands N]
     --from/--to pairs: only judge me in these time ranges (the parts where I am full screen); default the whole video.
     --expect-hands: hands I should show at most (2). A third hand is always a defect.

What it checks, per sampled frame (every 0.2 s by default, plus every frame of the first second):
  face      : one face found, face size steady (no sudden jump = morph), face landmarks not jumping.
  mouth     : lip gap / face height; first-second mouth; mouth vs. voice loudness correlation (lip sync).
  hands     : count (3+ = defect), two hands with the SAME handedness (two right hands = a known AI artefact),
              finger geometry (finger longer than 1.6x palm, fingertips collapsed onto each other = fused fingers,
              a fingertip far outside the hand = stretched finger), hand landmark jump between samples
              (a hand that teleports or melts), hands flickering in and out (appear/disappear within 0.4 s).
  glitches  : frame-to-frame pixel difference spikes (a cut, a flash, a melt), frozen runs (identical frames > 1 s).
  audio     : silence gaps > 1.2 s inside the voice, clipping.
  gaze      : eyes looking down / up / sideways (MediaPipe eye blendshapes) and head turned away
              (face matrix yaw). Over 40% of my full-screen samples off the lens = FAIL, 20-40% = warning.
              Calibrated on 6 reference renders: one with eyes visibly on the phone screen read 43% down = FAIL;
              the others read 27-33% = warning. MediaPipe reads a normal lens gaze as down 0.40-0.47. I talk INTO the lens.
Output: a table of flagged moments with timestamps, a PASS/FAIL line, a contact sheet (with flagged frames boxed red)
and a JSON. Exit code 0 = PASS, 3 = FAIL. A FAIL means: do not post; fix (edit around it with FFmpeg if the defect is in
a part I can cut or cover) or re-render with a corrected start picture / motion prompt.
It cannot see everything (a sixth finger that MediaPipe fits as five, a warped object): flagged and random frames are
also saved as big JPGs (qa_frames/) so they can be checked with every other tool available.
"""
import sys, os, math, json, subprocess, argparse
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
from kit_paths import MODELS as D

ap = argparse.ArgumentParser()
ap.add_argument('video')
ap.add_argument('--every', type=float, default=0.2)
ap.add_argument('--from', dest='frm', type=float, action='append', default=[])
ap.add_argument('--to', dest='to', type=float, action='append', default=[])
ap.add_argument('--sheet')
ap.add_argument('--json')
ap.add_argument('--expect-hands', type=int, default=2)
ap.add_argument('--frames-dir')
a = ap.parse_args()
ranges = list(zip(a.frm, a.to))

def in_ranges(t):
    return not ranges or any(s <= t <= e for s, e in ranges)

face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'face_landmarker.task')),
    output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=2))

def gaze_of(fres):
    """Eye direction + head turn from MediaPipe blendshapes / face matrix.
    down/up 0..1; side >0 = eyes to MY left (viewer's right), <0 = to my right; yaw/pitch in degrees."""
    b = {c.category_name: c.score for c in fres.face_blendshapes[0]}
    down = (b['eyeLookDownLeft'] + b['eyeLookDownRight']) / 2
    up = (b['eyeLookUpLeft'] + b['eyeLookUpRight']) / 2
    side = ((b['eyeLookOutLeft'] + b['eyeLookInRight']) - (b['eyeLookInLeft'] + b['eyeLookOutRight'])) / 2
    yaw = pitch = 0.0
    if fres.facial_transformation_matrixes:
        M = np.array(fres.facial_transformation_matrixes[0])
        yaw = math.degrees(math.atan2(M[0, 2], M[2, 2])); pitch = math.degrees(math.asin(max(-1, min(1, -M[1, 2]))))
    return {'down': round(down, 2), 'up': round(up, 2), 'side': round(side, 2), 'yaw': round(yaw, 1), 'pitch': round(pitch, 1)}

GAZE_DOWN, GAZE_UP, GAZE_SIDE, HEAD_YAW = 0.62, 0.55, 0.50, 22  # calibrated Oct 23 on 6 renders: normal down 0.40-0.47
hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'hand_landmarker.task')), num_hands=4,
    min_hand_detection_confidence=0.5, min_hand_presence_confidence=0.5))

def dist(p, q):
    return math.hypot(p.x - q.x, p.y - q.y)

def hand_issues(lm, W, H):
    iss = []
    palm = dist(lm[0], lm[9])
    if palm <= 0:
        return ['no palm']
    for i, j in ((5, 8), (9, 12), (13, 16), (17, 20)):
        if dist(lm[i], lm[j]) > 1.6 * palm:
            iss.append('finger long in 2d')   # mostly foreshortening noise: warning only
            break
    # 3D finger/palm ratio (x, y, z): the real 'stretched finger' test. A normal hand is about 1.1-1.4.
    d3 = lambda p, q: math.dist((p.x, p.y, p.z), (q.x, q.y, q.z))
    palm3 = d3(lm[0], lm[9]) or 1
    if max(d3(lm[i], lm[j]) for i, j in ((5, 8), (9, 12), (13, 16), (17, 20))) / palm3 > 1.75:
        iss.append('stretched finger')
    if dist(lm[2], lm[4]) > 1.5 * palm:
        iss.append('stretched thumb')
    tips = [lm[i] for i in (8, 12, 16, 20)]
    inside = [0 <= t.x <= 1 and 0 <= t.y <= 1 for t in tips]
    if all(inside):
        fused = 0
        for k in range(3):
            if dist(tips[k], tips[k + 1]) < 0.04 * palm:
                fused += 1
        if fused >= 2:
            iss.append('fingertips collapsed')
    # segment ratio sanity: proximal vs distal phalanges
    for b, m1, m2, t in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)):
        p1, p3 = dist(lm[b], lm[m1]), dist(lm[m2], lm[t])
        if p1 > 0 and p3 / p1 > 2.2:
            iss.append('odd finger joints')
            break
    return iss

cap = cv2.VideoCapture(a.video)
fps = cap.get(5) or 25
N = int(cap.get(7))
W, H = int(cap.get(3)), int(cap.get(4))
step = max(1, int(round(fps * a.every)))
rows, prev_gray, diffs, frames_keep = [], None, [], {}
i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    t = i / fps
    g = cv2.cvtColor(cv2.resize(fr, (180, 320)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    if prev_gray is not None:
        diffs.append((t, float(np.mean(np.abs(g - prev_gray)))))
    prev_gray = g
    if (i % step == 0 or t < 1.0) and in_ranges(t):
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        o = {'t': round(t, 2), 'flags': []}
        fres = face.detect(m)
        o['faces'] = len(fres.face_landmarks)
        if fres.face_landmarks:
            L = fres.face_landmarks[0]
            fh = abs(L[152].y - L[10].y)
            o['face_h'] = fh
            o['face_c'] = ((L[10].x + L[152].x) / 2, (L[10].y + L[152].y) / 2)
            o['mouth'] = abs(L[14].y - L[13].y) / fh if fh else 0
            gz = gaze_of(fres); o['gaze'] = gz
            if gz['down'] > GAZE_DOWN:
                o['flags'].append('eyes looking down')
            elif gz['up'] > GAZE_UP:
                o['flags'].append('eyes looking up')
            if abs(gz['side']) > GAZE_SIDE:
                o['flags'].append('eyes looking sideways')
            if abs(gz['yaw']) > HEAD_YAW:
                o['flags'].append('head turned away')
        else:
            o['flags'].append('no face')
        if o['faces'] > 1:
            o['flags'].append('second face')
        hres = hand.detect(m)
        hs = []
        for lm, hd in zip(hres.hand_landmarks, hres.handedness):
            hs.append({'side': hd[0].category_name[0], 'score': round(hd[0].score, 2),
                       'wrist': (lm[0].x, lm[0].y), 'pts': [(p.x, p.y) for p in lm],
                       'issues': hand_issues(lm, W, H)})
        o['hands'] = hs
        if len(hs) > a.expect_hands:
            o['flags'].append(f'{len(hs)} hands')
        if len(hs) == 2 and hs[0]['side'] == hs[1]['side'] and min(hs[0]['score'], hs[1]['score']) > 0.8:
            o['flags'].append('two ' + ('right' if hs[0]['side'] == 'R' else 'left') + ' hands')
        for h in hs:
            for s in h['issues']:
                o['flags'].append(s)
        rows.append(o)
        if i % step == 0:
            frames_keep[round(t, 2)] = cv2.resize(fr, (270, 480))
    i += 1
cap.release()

# temporal checks
for k in range(1, len(rows)):
    p, c = rows[k - 1], rows[k]
    dt = c['t'] - p['t']
    if dt <= 0 or dt > 0.5:
        continue
    if 'face_h' in p and 'face_h' in c:
        if abs(c['face_h'] - p['face_h']) / p['face_h'] > 0.18:
            c['flags'].append('face size jump')
        if math.hypot(c['face_c'][0] - p['face_c'][0], c['face_c'][1] - p['face_c'][1]) > 0.08:
            c['flags'].append('face position jump')
    # hand teleport: match by side
    for hc in c['hands']:
        same = [hp for hp in p['hands'] if hp['side'] == hc['side']]
        if same:
            hp = min(same, key=lambda h: math.hypot(h['wrist'][0] - hc['wrist'][0], h['wrist'][1] - hc['wrist'][1]))
            jump = math.hypot(hp['wrist'][0] - hc['wrist'][0], hp['wrist'][1] - hc['wrist'][1])
            if jump > 0.25 * (dt / 0.2):
                c['flags'].append('hand jump')
            # shape change: mean landmark distance after aligning wrists
            sh = np.mean([math.hypot((a2[0] - hc['wrist'][0]) - (b2[0] - hp['wrist'][0]),
                                     (a2[1] - hc['wrist'][1]) - (b2[1] - hp['wrist'][1]))
                          for a2, b2 in zip(hc['pts'], hp['pts'])])
            palm = math.hypot(hc['pts'][9][0] - hc['pts'][0][0], hc['pts'][9][1] - hc['pts'][0][1]) or 1
            if sh / palm > 0.9 * (dt / 0.2):
                c['flags'].append('hand shape morph')
# flicker: hand count changes up and back within 0.4 s
for k in range(1, len(rows) - 1):
    a0, a1, a2 = (len(rows[k + d]['hands']) for d in (-1, 0, 1))
    if a1 != a0 and a0 == a2 and rows[k + 1]['t'] - rows[k - 1]['t'] <= 0.45:
        rows[k]['flags'].append('hand flicker')

# pixel glitches
glitches = []
if diffs:
    vals = np.array([d for _, d in diffs])
    med = float(np.median(vals)) or 0.5
    for t, d in diffs:
        if d > max(6 * med, 18) and in_ranges(t):
            glitches.append((round(t, 2), round(d, 1)))
    frozen, run = [], 0
    for t, d in diffs:
        run = run + 1 if d < 0.05 else 0
        if run == int(fps * 1.0) and in_ranges(t):
            frozen.append(round(t, 2))
else:
    frozen = []

# audio + lip sync
sync = None; first_mouth = None; silences = []
try:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    au = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    if len(au):
        def rms(t0, t1):
            seg = au[int(t0 * 16000):int(t1 * 16000)]
            return float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0
        mt = [(r['t'], r['mouth']) for r in rows if 'mouth' in r]
        # Lip sync proxy (calibrated Oct 22 on 4 renders): the mouth must MOVE while the voice is on.
        # A 2 s voiced window where the lip gap range stays under 0.03 = mouth frozen while talking (defect).
        frozen_mouth = []
        if len(mt) > 10:
            for t0 in np.arange(0, mt[-1][0] - 2, 1.0):
                win_m = [m for t, m in mt if t0 <= t < t0 + 2]
                if len(win_m) >= 5 and rms(t0, t0 + 2) > 0.02 and (max(win_m) - min(win_m)) < 0.03:
                    frozen_mouth.append(round(float(t0), 1))
            voiced = [m for t, m in mt if rms(t - 0.05, t + 0.05) > 0.03]
            quiet_m = [m for t, m in mt if rms(t - 0.15, t + 0.15) < 0.005]
            sync = {'mouth_range_voiced': round(float(np.ptp(voiced)), 3) if voiced else None,
                    'mouth_mean_voiced': round(float(np.mean(voiced)), 3) if voiced else None,
                    'mouth_mean_quiet': round(float(np.mean(quiet_m)), 3) if quiet_m else None,
                    'frozen_mouth_windows': frozen_mouth}
        fm = [m for t, m in mt if t < 1.0]
        first_mouth = round(float(np.mean(fm)), 3) if fm else None
        win = 0.1; quiet = 0; t = 0.0; dur = len(au) / 16000
        peak = float(np.max(np.abs(au)))
        while t < dur:
            if rms(t, t + win) < 0.005:
                quiet += win
            else:
                if quiet > 1.2 and t - quiet > 0.5:
                    silences.append((round(t - quiet, 1), round(t, 1)))
                quiet = 0
            t += win
except Exception as e:
    print('audio check failed:', e)
    peak = 0

flagged = [r for r in rows if r['flags']]
hand_flag_times = [r['t'] for r in flagged if any('hand' in f or 'finger' in f or 'thumb' in f for f in r['flags'])]
counts = {}
for r in flagged:
    for f in r['flags']:
        counts[f] = counts.get(f, 0) + 1

problems, warns = [], []
sustained_stretch, run = [], 0
for r in rows:
    run = run + 1 if 'stretched finger' in r['flags'] else 0
    if run == 3:
        sustained_stretch.append(r['t'])
# Limits calibrated on the reference agent's renders: a render with a visible hand glitch had two right hands in 157 of
# 204 samples, stretched fingers in 38% and 13 hand jumps; clean renders had 0-2 two-right-hand
# samples, 21-27% 'stretched finger' (MediaPipe noise at 720p) and at most 4 hand jumps.
ns = max(1, len(rows))
hard_zero = ('3 hands', '4 hands', 'second face')
for f, n in counts.items():
    if f in hard_zero and n > 1:
        problems.append(f'{f} x{n}')
    elif f in ('two right hands', 'two left hands') and n > 2:
        problems.append(f'{f} x{n}')
    elif f == 'stretched finger' and sustained_stretch:
        problems.append(f'stretched finger held for 3+ samples at {sustained_stretch[:5]}')
    elif f == 'hand jump' and n > 6:
        problems.append(f'hand jump x{n}')
    elif f == 'no face' and n > 2:
        problems.append(f'no face x{n} (in my full-screen parts)')
    elif f == 'face size jump' and n > 1:
        problems.append(f'face size jump x{n}')
    elif f in ('hand shape morph', 'hand flicker', 'fingertips collapsed', 'odd finger joints', 'stretched thumb', 'finger long in 2d') and n / ns > 0.45:
        problems.append(f'{f} in {100*n/ns:.0f}% of samples')
    elif f in ('eyes looking down', 'eyes looking up', 'eyes looking sideways', 'head turned away') and n / ns > 0.40:
        problems.append(f'GAZE: {f} in {100*n/ns:.0f}% of samples (I must look into the lens)')
    elif f in ('eyes looking down', 'eyes looking up', 'eyes looking sideways', 'head turned away') and n / ns > 0.20:
        warns.append(f'GAZE WARNING: {f} in {100*n/ns:.0f}% of samples - look at those frames')
    elif n:
        warns.append(f'{f} x{n}')
if glitches:
    problems.append(f'pixel glitch at {glitches[:5]}')
if frozen:
    problems.append(f'frozen video at {frozen[:5]}')
if isinstance(sync, dict) and sync['frozen_mouth_windows']:
    problems.append(f"mouth frozen while voice plays at {sync['frozen_mouth_windows']}")
if silences:
    problems.append(f'silence gaps {silences}')

print(f'video={a.video} {W}x{H} {N/fps:.1f}s sampled={len(rows)} ranges={ranges or "all"}')
print(f'first_second_mouth={first_mouth} lip_sync={sync} audio_peak={peak:.2f}')
_g = [r['gaze'] for r in rows if 'gaze' in r]
if _g:
    gaze_summary = {k: round(float(np.median([x[k] for x in _g])), 2) for k in ('down', 'up', 'side', 'yaw', 'pitch')}
    first_g = [r['gaze'] for r in rows if 'gaze' in r and r['t'] < 1.0]
    print(f'gaze median={gaze_summary} first_second_down={round(float(np.mean([x["down"] for x in first_g])),2) if first_g else None} '
          f'(limits: down/up {GAZE_DOWN}, side {GAZE_SIDE}, head yaw {HEAD_YAW} deg; over 40% of samples = FAIL, 20-40% = warning)')
else:
    gaze_summary = None
print('warnings (look at these frames):', '; '.join(warns) or 'none')
print(f'flag counts: {counts}')
for r in flagged[:60]:
    print(f"  t={r['t']:5.2f}  {', '.join(r['flags'])}  hands=" + ' '.join(f"{h['side']}{h['score']}" for h in r['hands']))
print('RESULT:', 'PASS' if not problems else 'FAIL -> ' + '; '.join(problems))

# sheet
if a.sheet and frames_keep:
    keys = sorted(frames_keep)
    if len(keys) > 48:
        idx = np.linspace(0, len(keys) - 1, 48).astype(int); keys = [keys[j] for j in idx]
    flag_t = {r['t'] for r in flagged}
    tiles = []
    for k in keys:
        im = frames_keep[k].copy()
        if k in flag_t:
            cv2.rectangle(im, (0, 0), (269, 479), (0, 0, 255), 8)
        cv2.putText(im, f'{k:.1f}s', (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        tiles.append(im)
    while len(tiles) % 8:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[r:r + 8]) for r in range(0, len(tiles), 8)])
    cv2.imwrite(a.sheet, sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
if a.json:
    json.dump({'problems': problems, 'counts': counts, 'sync': sync, 'first_mouth': first_mouth, 'gaze': gaze_summary,
               'glitches': glitches, 'frozen': frozen, 'silences': silences,
               'flagged': [{'t': r['t'], 'flags': r['flags']} for r in flagged]}, open(a.json, 'w'), indent=1)
sys.exit(0 if not problems else 3)
