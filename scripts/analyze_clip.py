#!/usr/bin/env python3
"""Find the listening-pause window and a bright still frame in a trend clip.

Usage: analyze_clip.py CLIP.mp4 [--pause 13] [--still OUT.png] [--whisper]

Prints per-second loudness (RMS dBFS), the loudest window of --pause seconds
(a good pause offset), the brightest frame time in the first 10 s, and with
--whisper a timed transcript (faster_whisper small, cpu int8) so the pause can
start on the hook or the quoted line. --still writes that bright frame as PNG
for the hook-section window.
"""
import argparse, subprocess, sys, math
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("clip")
ap.add_argument("--pause", type=float, default=13.0)
ap.add_argument("--still")
ap.add_argument("--still-search", type=float, default=10.0, help="seconds to search for a bright frame")
ap.add_argument("--whisper", action="store_true")
a = ap.parse_args()

sr = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", a.clip, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
secs = len(x) // sr
rms = [float(np.sqrt(np.mean(x[i*sr:(i+1)*sr]**2)) + 1e-9) for i in range(secs)]
db = [20*math.log10(r) for r in rms]
print(f"duration {len(x)/sr:.2f} s")
print("per-second RMS dBFS:")
print(" ".join(f"{i}:{d:.0f}" for i, d in enumerate(db)))
P = int(round(a.pause))
if secs > P:
    best = max(range(0, secs - P + 1), key=lambda s: sum(rms[s:s+P]))
    print(f"loudest {P}s window starts at {best} s (candidate pause offset)")

# brightness per frame at 4 fps
W, H = 108, 192
raw = subprocess.run(["ffmpeg", "-v", "error", "-t", str(a.still_search), "-i", a.clip, "-vf", f"fps=4,scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
n = len(raw) // (W*H)
bright = [float(np.frombuffer(raw[i*W*H:(i+1)*W*H], dtype=np.uint8).mean()) for i in range(n)]
if bright:
    cand = [i for i in range(n) if i >= 2] or list(range(n))   # skip the first half second (often black)
    bi = max(cand, key=lambda i: bright[i])
    t = bi / 4.0
    print(f"brightest frame in first {a.still_search:.0f} s: t={t:.2f} s (mean {bright[bi]:.0f}/255)")
    if a.still:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.clip, "-frames:v", "1", a.still], check=True)
        print(f"still written: {a.still}")

if a.whisper:
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    # pass the already-decoded 16 kHz audio: newer PyAV rejects faster_whisper's own file decoder (Oct 17 fix)
    segs, info = m.transcribe(x, vad_filter=False)
    print(f"transcript (language {info.language}):")
    for s in segs:
        print(f"  {s.start:6.2f}-{s.end:6.2f}  {s.text.strip()}")
