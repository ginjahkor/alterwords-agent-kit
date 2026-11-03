#!/usr/bin/env python3
"""Compare the agent's face in new look previews against its main close-up (AGENT_REF_IMAGE).
Usage: face_check.py IMAGE [IMAGE ...]   (reference: AGENT_REF_IMAGE in settings.env)
OpenCV YuNet detector + SFace recognizer. SFace cosine similarity >= 0.363 is OpenCV's "same person" threshold;
for the reference agent we wanted >= 0.50 (its own original looks scored in that range). Prints face size as a share of image height,
because a small face hurts lip sync.
"""
import sys, os, cv2, numpy as np
from kit_paths import LOOKS as D, MODELS, setting
REF = setting('AGENT_REF_IMAGE', os.path.join(D, 'reference.jpg'))
det = None
rec = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'sface.onnx'), '')

def feat(path):
    global det
    img = cv2.imread(path)
    h, w = img.shape[:2]
    s = 1280 / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)))
        h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'yunet.onnx'), '', (w, h), 0.7)
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None, 0, 0, None
    f = max(faces, key=lambda r: r[2] * r[3])
    al = rec.alignCrop(img, f)
    sc = max(1080 / w, 1920 / h); oy = (h * sc - 1920) / 2
    return rec.feature(al), f[3] / h, len(faces), (f[1] * sc - oy, (f[1] + f[3]) * sc - oy)

ref = feat(REF)[0]
for p in sys.argv[1:]:
    fe, share, n, fy = feat(p)
    if fe is None:
        print(f'{os.path.basename(p)}\tNO FACE FOUND')
        continue
    cos = rec.match(ref, fe, cv2.FaceRecognizerSF_FR_COSINE)
    verdict = 'match' if cos >= 0.60 else ('weak' if cos >= 0.363 else 'DIFFERENT')
    print(f'{os.path.basename(p)}\tcos={cos:.3f}\t{verdict}\tface_height={share*100:.0f}%\tface_y={fy[0]:.0f}-{fy[1]:.0f}\tfaces={n}')
