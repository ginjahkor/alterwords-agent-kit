#!/usr/bin/env python3
"""Strict hand check for a START PICTURE (a look), Rules 3-5 of the standing rules.
Make two matching pictures of the same look showing different parts (the full frame and a close-up of the
hands / upper body) and check both, so the hands are right BEFORE the picture goes to the video generator.

Usage: hand_check.py IMAGE [IMAGE2 ...] [--closeups OUTDIR] [--expect 1|2]
  For each image: detects hands on the full frame, then cuts a close-up around every hand (and the upper body) at full
  resolution, saves them (the second picture of the same look) and runs the detector again on each close-up.
  If IMAGE2 is given (a second generated picture of the same look, e.g. a close-up), it is checked the same way.
FAIL reasons (any one = do not use this picture):
  - two hands with the same handedness (two right hands), on the full frame or the close-ups
  - more hands than --expect (default: 1 for a selfie look, 2 for propped), or a hand found on the full frame that the
    close-up cannot confirm (or the reverse), or handedness that flips between full frame and close-up
  - a visible hand with fewer than 5 fingertips inside the picture (cut-off fingers are fine only at the picture edge)
  - finger longer than 1.6x the palm, a stretched thumb, fingertips collapsed onto each other, odd joint ratios
  - a visible phone is checked separately by object_check.py
Exit 0 = PASS, 3 = FAIL.
"""
import sys, os, math, argparse, cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
from kit_paths import MODELS as D
ap = argparse.ArgumentParser()
ap.add_argument('images', nargs='+')
ap.add_argument('--closeups')
ap.add_argument('--expect', type=int, default=2)
a = ap.parse_args()
hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'hand_landmarker.task')), num_hands=4,
    min_hand_detection_confidence=0.4, min_hand_presence_confidence=0.4))

def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])

def detect(img):
    m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
    r = hand.detect(m)
    out = []
    h, w = img.shape[:2]
    for lm, hd in zip(r.hand_landmarks, r.handedness):
        pts = [(p.x * w, p.y * h) for p in lm]
        out.append({'side': hd[0].category_name, 'score': hd[0].score, 'pts': pts})
    return out

def issues(hd, w, h):
    p = hd['pts']; iss = []
    palm = dist(p[0], p[9]) or 1
    for i, j in ((5, 8), (9, 12), (13, 16), (17, 20)):
        if dist(p[i], p[j]) > 1.6 * palm:
            iss.append('stretched finger'); break
    if dist(p[2], p[4]) > 1.5 * palm:
        iss.append('stretched thumb')
    tips = [p[i] for i in (4, 8, 12, 16, 20)]
    margin = 0.01
    inside = [margin * w <= x <= (1 - margin) * w and margin * h <= y <= (1 - margin) * h for x, y in tips]
    near_edge = any(not v for v in inside)
    if sum(inside) < 5 and not near_edge:
        iss.append(f'{sum(inside)} fingertips')
    t4 = tips[1:]
    if sum(1 for k in range(3) if dist(t4[k], t4[k + 1]) < 0.04 * palm) >= 2:
        iss.append('fingertips collapsed')
    for b, m1, m2, t in ((5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)):
        p1, p3 = dist(p[b], p[m1]), dist(p[m2], p[t])
        if p1 > 0 and p3 / p1 > 2.2:
            iss.append('odd finger joints'); break
    return iss

fail_all = False
for path in a.images:
    img = cv2.imread(path)
    if img is None:
        print(f'{path}\tcannot read'); fail_all = True; continue
    h, w = img.shape[:2]
    full = detect(img)
    fails = []
    sides = [x['side'] for x in full if x['score'] > 0.7]
    if len(sides) != len(set(sides)):
        fails.append('two ' + sides[0].lower() + ' hands (full frame)')
    if len(full) > a.expect:
        fails.append(f'{len(full)} hands, expected at most {a.expect}')
    rep = [f"{x['side'][0]}{x['score']:.2f}" for x in full]
    crops = []
    for k, x in enumerate(full):
        for s in issues(x, w, h):
            fails.append(f'hand {k} {s} (full)')
        xs = [q[0] for q in x['pts']]; ys = [q[1] for q in x['pts']]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        size = max(max(xs) - min(xs), max(ys) - min(ys)) * 2.2
        x0, y0 = int(max(0, cx - size / 2)), int(max(0, cy - size / 2))
        x1, y1 = int(min(w, cx + size / 2)), int(min(h, cy + size / 2))
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        crop = cv2.resize(crop, None, fx=max(1, 640 / max(crop.shape[:2])), fy=max(1, 640 / max(crop.shape[:2])))
        cd = detect(crop)
        if a.closeups:
            os.makedirs(a.closeups, exist_ok=True)
            cv2.imwrite(os.path.join(a.closeups, f'{os.path.splitext(os.path.basename(path))[0]}_hand{k}.jpg'), crop)
        if not cd:
            fails.append(f'hand {k} not confirmed in close-up')
            continue
        best = max(cd, key=lambda d: d['score'])
        if best['side'] != x['side'] and best['score'] > 0.7 and x['score'] > 0.7:
            fails.append(f'hand {k} handedness flips in close-up ({x["side"]} -> {best["side"]})')
        for s in issues(best, crop.shape[1], crop.shape[0]):
            fails.append(f'hand {k} {s} (close-up)')
        crops.append(f"{best['side'][0]}{best['score']:.2f}")
    # upper-body close-up: the middle 70% width, top 75% height, checked for an extra hand
    ub = img[int(h * 0.1):int(h * 0.85), int(w * 0.1):int(w * 0.9)]
    ubd = detect(ub)
    if a.closeups:
        cv2.imwrite(os.path.join(a.closeups, f'{os.path.splitext(os.path.basename(path))[0]}_upper.jpg'), ub)
    us = [x['side'] for x in ubd if x['score'] > 0.7]
    if len(us) != len(set(us)):
        fails.append('two ' + us[0].lower() + ' hands (upper-body close-up)')
    if len(ubd) > a.expect:
        fails.append(f'{len(ubd)} hands in upper-body close-up')
    res = 'PASS' if not fails else 'FAIL'
    fail_all |= bool(fails)
    print(f"{os.path.basename(path)}\t{res}\tfull={' '.join(rep) or 'no hands'}\tcloseups={' '.join(crops) or '-'}\tupper={len(ubd)}" + (f"\t{'; '.join(fails)}" if fails else ''))
sys.exit(3 if fail_all else 0)
