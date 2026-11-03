#!/usr/bin/env python3
"""Check a look picture (or video frames) for the things that make my videos move well or look stiff.
Usage: pose_check.py IMAGE [IMAGE ...]
       pose_check.py --video FILE.mp4 [--every 0.5]     (mouth and hands over time in a render)
Prints per image:
  mouth   = lip gap / face height (MediaPipe face landmarks 13-14 vs 10-152). Closed < 0.02, slightly open 0.03-0.10,
            wide > 0.12. Owner (Oct 22): every starting picture needs the mouth slightly open.
  smile   = mouthSmile blendshape average (0-1), brows = browInnerUp (expression), jaw = jawOpen blendshape.
  hands   = hands found, with how many fingertips are inside the frame and a rough 'raised' flag (wrist above the
            bottom 15% of the picture). A free, visible hand is what lets Avatar IV gesture.
  warn    = more than 2 hands, a hand with odd geometry (finger longer than 1.6x the palm, or fingers crossing the
            palm), or no face.
It cannot see warped phones or a sixth finger reliably: always look at the preview contact sheet as well.
"""
import sys, os, math, cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
from kit_paths import MODELS as D
face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'face_landmarker.task')),
    output_face_blendshapes=True, num_faces=2))
hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'hand_landmarker.task')), num_hands=4,
    min_hand_detection_confidence=0.4))

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def check(img):
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    out = {}
    fr = face.detect(m)
    if not fr.face_landmarks:
        out['warn'] = 'no face'
    else:
        L = fr.face_landmarks[0]
        fh = abs(L[152].y - L[10].y) * h
        gap = abs(L[14].y - L[13].y) * h
        out['mouth'] = gap / fh if fh else 0
        bs = {c.category_name: c.score for c in fr.face_blendshapes[0]}
        out['smile'] = (bs.get('mouthSmileLeft', 0) + bs.get('mouthSmileRight', 0)) / 2
        out['brows'] = bs.get('browInnerUp', 0)
        out['jaw'] = bs.get('jawOpen', 0)
        out['face_h'] = fh / h
    hr = hand.detect(m)
    hands, warns = [], []
    for lm, hd in zip(hr.hand_landmarks, hr.handedness):
        palm = dist(lm[0], lm[9])
        tips = sum(1 for i in (4, 8, 12, 16, 20) if 0 <= lm[i].x <= 1 and 0 <= lm[i].y <= 1)
        longest = max(dist(lm[i], lm[j]) for i, j in ((5, 8), (9, 12), (13, 16), (17, 20)))
        if palm > 0 and longest > 1.6 * palm:
            warns.append('odd finger length')
        raised = lm[0].y < 0.85
        hands.append(f"{hd[0].category_name[0]}:{tips}tips{'/raised' if raised else ''}")
    if len(hands) > 2:
        warns.append(f'{len(hands)} hands')
    out['hands'] = hands
    if warns:
        out['warn'] = (out.get('warn', '') + ' ' + ', '.join(warns)).strip()
    return out

def fmt(name, o):
    if 'mouth' not in o:
        return f"{name}\tNO FACE\thands={len(o['hands'])} {' '.join(o['hands'])}"
    state = 'closed' if o['mouth'] < 0.02 else ('slightly open' if o['mouth'] <= 0.12 else 'wide')
    return (f"{name}\tmouth={o['mouth']:.3f} ({state})\tsmile={o['smile']:.2f}\tbrows={o['brows']:.2f}\tjaw={o['jaw']:.2f}"
            f"\tface_h={o['face_h']*100:.0f}%\thands={len(o['hands'])} {' '.join(o['hands'])}" + (f"\tWARN: {o['warn']}" if o.get('warn') else ''))

if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--video':
        f = a[1]; every = float(a[3]) if len(a) > 3 else 0.5
        cap = cv2.VideoCapture(f); fps = cap.get(5) or 25; step = max(1, int(fps * every)); i = 0; rows = []
        while True:
            ok, fr = cap.read()
            if not ok: break
            if i % step == 0:
                o = check(fr); rows.append(o)
            i += 1
        mo = [r['mouth'] for r in rows if 'mouth' in r]
        nh = [len(r['hands']) for r in rows]
        print(f"{os.path.basename(os.path.dirname(f)) or f}\tframes={len(rows)}\tfirst_mouth={mo[0] if mo else 0:.3f}\tmouth_mean={np.mean(mo):.3f}"
              f"\tmouth_max={max(mo):.3f}\tsmile_mean={np.mean([r['smile'] for r in rows if 'smile' in r]):.2f}"
              f"\tframes_with_hand={sum(1 for n in nh if n)/len(nh)*100:.0f}%")
    else:
        for p in a:
            img = cv2.imread(p)
            if img is None:
                print(f'{p}\tcannot read'); continue
            print(fmt(os.path.basename(p), check(img)))
