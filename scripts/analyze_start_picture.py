#!/usr/bin/env python3
"""Analyze EVERY part of my starting picture before a HeyGen render, then draft the motion prompt from it.
Describe every part of the frame so the motion prompt matches it exactly. Pairs with PROMPT_TEMPLATE.md.

Usage: analyze_start_picture.py IMAGE [--look L39] [--json out.json] [--prompt-out motion_prompt.txt]

Measures (MediaPipe face/hand landmarks, YOLOX objects):
  eyes   : where my eyes point (eye blendshapes: down/up/side) -> INTO LENS / DOWN / TO MY LEFT / TO MY RIGHT
  head   : head yaw/pitch in degrees from the face matrix -> facing camera / turned to my left/right / tilted
  face   : box and position in the frame (left / centre / right third; top of head y) and mouth gap
  body   : shoulder/torso direction guessed from the face position + yaw (no pose model on this machine)
  hands  : count, side of the PICTURE each is on, height (chin / chest / waist / bottom edge), palm toward camera
           or not, fingers extended, touching the frame edge (= arm holding the phone off-frame)
  objects: phone, cup, laptop, book, mic... (YOLOX); a second person (YOLOX person count)
  background: from looks/catalog.json for the look (the catalog text was written from the look's own prompt)
Prints a frame description + PROBLEMS (gaze off lens, 2+ hands on one side, extra person, warped hand...).
If eyes are not INTO LENS or the head is turned > 15 deg, do NOT render this picture: remake it (1 credit) with
'looking directly into the camera lens' in the picture prompt, or pick another look.
"""
import sys, os, json, math, argparse
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

from kit_paths import MODELS as D, LOOKS
ap = argparse.ArgumentParser()
ap.add_argument('image'); ap.add_argument('--look'); ap.add_argument('--json'); ap.add_argument('--prompt-out')
a = ap.parse_args()

img = cv2.imread(a.image)
if img is None:
    sys.exit(f'cannot read {a.image}')
H, W = img.shape[:2]
rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'face_landmarker.task')),
    output_face_blendshapes=True, output_facial_transformation_matrixes=True, num_faces=3))
hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, 'hand_landmarker.task')), num_hands=4,
    min_hand_detection_confidence=0.3))
out = {'image': a.image, 'size': [W, H], 'problems': [], 'notes': []}
P = out['problems']

# ---------- face, eyes, head ----------
fr = face.detect(rgb)
if not fr.face_landmarks:
    P.append('NO FACE found')
else:
    if len(fr.face_landmarks) > 1:
        P.append(f'{len(fr.face_landmarks)} faces in the picture (a stranger?)')
    L = fr.face_landmarks[0]
    xs = [p.x for p in L]; ys = [p.y for p in L]
    b = {c.category_name: c.score for c in fr.face_blendshapes[0]}
    down = (b['eyeLookDownLeft'] + b['eyeLookDownRight']) / 2
    up = (b['eyeLookUpLeft'] + b['eyeLookUpRight']) / 2
    side = ((b['eyeLookOutLeft'] + b['eyeLookInRight']) - (b['eyeLookInLeft'] + b['eyeLookOutRight'])) / 2
    M = np.array(fr.facial_transformation_matrixes[0])
    yaw = math.degrees(math.atan2(M[0, 2], M[2, 2])); pitch = math.degrees(math.asin(max(-1, min(1, -M[1, 2]))))
    # eyes (thresholds calibrated Oct 23 on the reference agent's renders: a normal lens gaze reads down 0.40-0.47)
    if down > 0.62:
        eyes = 'DOWN (at a phone screen or the floor), not into the lens'
    elif up > 0.55:
        eyes = 'UP, not into the lens'
    elif side > 0.40:
        eyes = "TO MY LEFT (viewer's right), not into the lens"
    elif side < -0.40:
        eyes = "TO MY RIGHT (viewer's left), not into the lens"
    else:
        eyes = 'INTO THE LENS'
    if yaw > 15:
        head = f"turned {yaw:.0f} deg to my left (viewer's right)"
    elif yaw < -15:
        head = f"turned {-yaw:.0f} deg to my right (viewer's left)"
    else:
        head = f'facing the camera (yaw {yaw:.0f} deg)'
    head += f', chin {"down" if pitch > 10 else "up" if pitch < -10 else "level"} (pitch {pitch:.0f})'
    fcx = (min(xs) + max(xs)) / 2
    third = 'left third' if fcx < 0.40 else 'right third' if fcx > 0.60 else 'centre'
    fh = max(ys) - min(ys)
    mouth = abs(L[14].y - L[13].y) / fh if fh else 0
    out['face'] = {'box_px': [round(min(xs) * W), round(min(ys) * H), round(max(xs) * W), round(max(ys) * H)],
                   'position': third, 'top_of_face_y': round(min(ys) * H), 'height_frac': round(fh, 3),
                   'mouth_gap': round(mouth, 3)}
    out['eyes'] = {'reading': eyes, 'down': round(down, 2), 'up': round(up, 2), 'side': round(side, 2)}
    out['head'] = {'reading': head, 'yaw': round(yaw, 1), 'pitch': round(pitch, 1)}
    if not eyes.startswith('INTO'):
        P.append(f'GAZE: eyes {eyes}. Remake the picture with "looking directly into the camera lens" or pick another look')
    if abs(yaw) > 15:
        P.append(f'HEAD: {head}. The render will keep that turn; remake or pick another look')
    if mouth < 0.02:
        P.append('MOUTH closed (owner rule: slightly open)')
    elif mouth > 0.12:
        P.append('MOUTH too wide')
    # body direction from face position (selfie arm pulls the torso) + yaw
    out['body'] = {'reading': ('turned with my head, ' if abs(yaw) > 10 else 'square to the camera, ') +
                   f'face in the {third} of the frame'}

# ---------- hands ----------
hr = hands.detect(rgb)
hl = []
for i, lm in enumerate(hr.hand_landmarks):
    xs = [p.x for p in lm]; ys = [p.y for p in lm]
    label = hr.handedness[i][0].category_name if hr.handedness else '?'
    # MediaPipe's left/right label is unreliable on my generated pictures (some look mirrored like a front camera,
    # some not), so prompts describe each hand by WHERE IT IS IN THE PICTURE, and the phone hand comes from the catalog.
    mine = {'Left': 'right', 'Right': 'left'}.get(label, '?')
    wy = lm[0].y; cx = sum(xs) / 21
    where = 'left side of the picture' if cx < 0.4 else 'right side of the picture' if cx > 0.6 else 'middle of the picture'
    fy = out.get('face', {}).get('box_px', [0, 0, 0, H * 0.4])[3] / H
    height = ('at chin/face height' if wy < fy + 0.05 else 'at chest height' if wy < fy + 0.25 else
              'at waist height' if wy < 0.93 else 'at the bottom edge')
    edge = min(xs) < 0.02 or max(xs) > 0.98 or max(ys) > 0.98
    # palm toward camera: wrist->index MCP x wrist->pinky MCP normal z sign (rough)
    v1 = np.array([lm[5].x - lm[0].x, lm[5].y - lm[0].y, lm[5].z - lm[0].z])
    v2 = np.array([lm[17].x - lm[0].x, lm[17].y - lm[0].y, lm[17].z - lm[0].z])
    nz = np.cross(v1, v2)[2]
    palm = 'palm toward camera' if (nz < 0) == (mine == 'right') else 'back of hand toward camera'
    ext = 0
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        if math.dist((lm[tip].x, lm[tip].y), (lm[0].x, lm[0].y)) > math.dist((lm[pip].x, lm[pip].y), (lm[0].x, lm[0].y)):
            ext += 1
    palm_len = math.dist((lm[0].x, lm[0].y), (lm[9].x, lm[9].y)) or 1e-6
    longest = max(math.dist((lm[t].x, lm[t].y), (lm[t - 3].x, lm[t - 3].y)) for t in (8, 12, 16, 20)) / palm_len
    role = 'phone arm (holding the phone just off-frame)' if edge and wy < 0.85 else 'free hand'
    h = {'role': role, 'mediapipe_label': label, 'my_hand': mine, 'where': where, 'height': height, 'palm': palm, 'fingers_extended_of_4': ext,
         'touches_frame_edge': edge, 'finger_to_palm': round(longest, 2)}
    if longest > 1.6:
        P.append(f'HAND: my {mine} hand has a stretched finger ({longest:.2f}x palm)')
    hl.append(h)
out['hands'] = hl
sides = [h['my_hand'] for h in hl]
for s in ('left', 'right'):
    if sides.count(s) > 1:
        P.append(f'HANDS: {sides.count(s)} {s} hands detected (the 5 PM study-desk bug). Do not render')
if len(hl) > 2:
    P.append(f'HANDS: {len(hl)} hands in the picture')

# ---------- objects ----------
import subprocess
try:
    oc = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'object_check.py'), a.image],
                        capture_output=True, text=True, timeout=120).stdout.strip().splitlines()
    out['objects'] = oc[0].split('\t', 1)[1] if oc and '\t' in oc[0] else (oc[0] if oc else '')
except Exception as e:
    out['objects'] = f'object check failed: {e}'
import re
_m = re.search(r'big (\d+)', str(out['objects']))
if _m and int(_m.group(1)) > 1:
    P.append(f"PEOPLE: {out['objects']} (a second big person close to me)")
elif 'people=' in str(out['objects']) and not str(out['objects']).split('people=')[1].startswith('1'):
    out['notes'].append('small background people: tell the prompt the background stays still')
if 'phone=0' not in str(out['objects']) and 'phone=' in str(out['objects']):
    out['notes'].append('a phone is visible in the picture: say exactly which hand holds it and that it stays still')

# ---------- background from the catalog ----------
look = None
if a.look:
    try:
        look = next(e for e in json.load(open(os.path.join(LOOKS, 'catalog.json'))) if e.get('code') == a.look)
    except Exception:
        look = None
if look:
    out['look'] = {k: look.get(k) for k in ('code', 'outfit', 'framing', 'background', 'phone_side', 'style')}

# ---------- frame description ----------
print(f'== START PICTURE ANALYSIS: {a.image} ({W}x{H})')
if 'eyes' in out:
    print(f"EYES : {out['eyes']['reading']}  (down {out['eyes']['down']}, up {out['eyes']['up']}, side {out['eyes']['side']})")
    print(f"HEAD : {out['head']['reading']}")
    print(f"FACE : {out['face']['position']}, top of face at y={out['face']['top_of_face_y']}, mouth gap {out['face']['mouth_gap']}")
    print(f"BODY : {out['body']['reading']}")
for h in hl:
    print(f"HAND : {h['role']}: {h['where']}, {h['height']}, {h['palm']}, {h['fingers_extended_of_4']}/4 fingers out"
          + (', reaches the frame edge' if h['touches_frame_edge'] else '') + f" (MediaPipe label {h['mediapipe_label']}, unreliable)")
print(f"OBJECTS: {out['objects']}")
if not hl:
    print('HAND : no hand visible (phone arm is off-frame; keep it that way in the prompt)')
if look:
    print(f"LOOK : {look.get('code')} {look.get('style')} | phone in my {look.get('phone_side')} hand | outfit: {look.get('outfit')}")
    print(f"BACKGROUND: {look.get('background')} | framing: {look.get('framing')}")
for n_ in out['notes']:
    print('NOTE : ' + n_)
print('PROBLEMS: ' + ('; '.join(P) if P else 'none'))
print('RESULT: ' + ('FAIL - fix the picture before rendering' if P else 'PASS - write the prompt from this description'))

# ---------- draft motion prompt (PROMPT_TEMPLATE.md section C) ----------
# HeyGen's own rule (help article 12805098): one gesture + one expression, under two short clauses, no props, no
# camera moves, motion only covers the first 10 s then loops/holds. So the long frame description above is for ME
# (and for the picture prompt); the motion prompt is the short, exact version of it: GAZE first, then STILLNESS of
# the phone arm, then ONE free-hand gesture named by where that hand is in the picture.
phone = (look or {}).get('phone_side') or 'right'
visible_free = [h for h in hl if h['role'] == 'free hand']
gaze = 'Looks straight into the camera lens the whole time, warm and confident'
if phone == 'propped':
    still = 'hands stay relaxed in the lap'
else:
    still = f'the {phone} arm holding the phone stays still'
if visible_free:
    h = visible_free[0]
    side_word = h['where'].replace(' of the picture', '').replace('side', '').strip()
    gest = f'the free hand on the {side_word} of the frame makes small slow open-palm gestures, five relaxed fingers'
else:
    gest = 'the head makes gentle natural nods'
prompt = f'{gaze}; {still}, and {gest}.'
out['draft_prompt'] = prompt
print('DRAFT MOTION PROMPT (HeyGen: keep it this short; every clause must match the analysis above):')
print(prompt)
if a.prompt_out:
    open(a.prompt_out, 'w').write(prompt + '\n')
if a.json:
    json.dump(out, open(a.json, 'w'), indent=1)
sys.exit(1 if P else 0)
