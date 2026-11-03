#!/usr/bin/env python3
"""Second automatic check on a look picture: what objects are in it (YOLOX-S, COCO classes, OpenCV DNN).
Usage: object_check.py IMAGE [IMAGE ...]
Flags what makes a selfie look fake or broken:
  phone  = a cell phone visible in the picture (selfie looks should keep the phone out of frame; a visible phone is
           where AI warping shows). Prints its box and size.
  people = how many people are detected. More than one big person near me = a second face that HeyGen may animate.
It does not judge hands or faces: pose_check.py and face_check.py do that, and the owner eyeballs the contact sheet.
"""
import sys, os, cv2, numpy as np
from kit_paths import MODELS
M = os.path.join(MODELS, 'yolox_s.onnx')
COCO = {0: 'person', 67: 'cell phone', 41: 'cup', 63: 'laptop', 39: 'bottle', 56: 'chair', 2: 'car', 5: 'bus', 62: 'tv'}
net = cv2.dnn.readNet(M)
S = 640

def detect(img):
    h, w = img.shape[:2]; r = min(S / h, S / w)
    pad = np.full((S, S, 3), 114, np.uint8); rs = cv2.resize(img, (int(w * r), int(h * r)))
    pad[:rs.shape[0], :rs.shape[1]] = rs
    blob = cv2.dnn.blobFromImage(pad.astype(np.float32), 1.0, (S, S), swapRB=False)
    net.setInput(blob); out = net.forward()[0]
    grids, strides = [], []
    for s in (8, 16, 32):
        n = S // s; xv, yv = np.meshgrid(np.arange(n), np.arange(n))
        grids.append(np.stack((xv, yv), 2).reshape(-1, 2)); strides.append(np.full((n * n, 1), s))
    g = np.concatenate(grids); st = np.concatenate(strides)
    out[:, :2] = (out[:, :2] + g) * st; out[:, 2:4] = np.exp(out[:, 2:4]) * st
    scores = out[:, 4:5] * out[:, 5:]; cls = scores.argmax(1); conf = scores.max(1)
    keep = conf > 0.35
    b = out[keep, :4]; cls = cls[keep]; conf = conf[keep]
    boxes = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2, b[:, 2], b[:, 3]], 1) / r
    idx = cv2.dnn.NMSBoxes(boxes.tolist(), conf.tolist(), 0.35, 0.5)
    res = []
    for i in np.array(idx).flatten():
        x, y, bw, bh = boxes[i]; res.append((int(cls[i]), float(conf[i]), x / w, y / h, bw / w, bh / h))
    return res

for p in sys.argv[1:]:
    img = cv2.imread(p)
    if img is None:
        print(f'{p}\tcannot read'); continue
    d = detect(img)
    people = [x for x in d if x[0] == 0]
    big = [x for x in people if x[5] > 0.35]
    phones = [x for x in d if x[0] == 67]
    other = sorted({COCO[x[0]] for x in d if x[0] in COCO and x[0] not in (0, 67)})
    flag = []
    if phones: flag.append('PHONE VISIBLE ' + ', '.join(f"conf {x[1]:.2f} at x{x[2]*100:.0f}% y{x[3]*100:.0f}% size {x[4]*100:.0f}x{x[5]*100:.0f}%" for x in phones))
    if len(big) > 1: flag.append(f'{len(big)} big people')
    print(f"{os.path.basename(p)}\tpeople={len(people)} (big {len(big)})\tphone={len(phones)}\tother={','.join(other) or '-'}" + (f"\tFLAG: {'; '.join(flag)}" if flag else ''))
