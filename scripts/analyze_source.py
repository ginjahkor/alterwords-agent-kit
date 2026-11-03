#!/usr/bin/env python3
"""Understand a source video BEFORE cutting it.

Usage:
  analyze_source.py SRC.mp4 [--out DIR] [--model small] [--lang en] [--lens 4,6,10]
                    [--speech] [--no-transcript] [--top 3]

What it does (all local, free, CPU):
  1. Transcript with WORD-level timestamps (faster-whisper). Music mode by default (no VAD, so
     singing is kept); --speech turns VAD on for interviews/podcasts. Drops hallucinated words
     that fall in silence.
  2. Scenes / shot changes (PySceneDetect AdaptiveDetector) + one keyframe per scene.
  3. Audio: loudness per 0.25 s, beats + tempo, onset strength, the biggest energy RISES
     (the "drop" / chorus entry = best hook moments), repeated lyric lines (chorus).
  4. Picture: what each shot shows (CLIP labels, --find to locate a moment), face-on-screen share, motion, brightness per second; OCR of on-screen text
     (tesseract) per scene with WHERE the text sits, so my captions do not cover it.
  5. Suggested cut ranges for each length in --lens, snapped so they never start or end
     mid-word, preferring line starts, beats and shot changes. For each suggestion it writes
     cut_<len>s_<n>.srt and cut_<len>s_<n>_words.json with times RELATIVE to the cut start,
     ready for timed captions (FFmpeg subtitles or a HyperFrames caption composition).

Outputs in DIR (default: <src>_analysis/):
  timeline.md        human-readable timeline (read this first)
  timeline.json      everything, machine-readable
  transcript.srt     full timed subtitles
  words.json         every word [{id,text,start,end}] (HyperFrames caption format)
  contact_sheet.jpg  one frame per scene with timestamps (shot labels come from describe_frames.py, CLIP)
  frames/            keyframes
"""
import argparse, json, math, os, re, subprocess, sys, collections
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out")
ap.add_argument("--model", default="small")
ap.add_argument("--lang", default="en", help="default en (Naija English/pidgin; auto-detect calls it Yoruba and returns junk). Use auto for auto-detect")
ap.add_argument("--lens", default="4,6,10")
ap.add_argument("--top", type=int, default=3)
ap.add_argument("--beam", type=int, default=2)
ap.add_argument("--speech", action="store_true", help="spoken video: use VAD")
ap.add_argument("--no-transcript", action="store_true")
ap.add_argument("--find", action="append", default=[], help='describe a moment to locate, e.g. --find "a man kneeling with a ring" (repeatable)')
a = ap.parse_args()

SRC = os.path.abspath(a.src)
OUT = os.path.abspath(a.out or os.path.splitext(SRC)[0] + "_analysis")
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)

def log(*x):
    print(*x, file=sys.stderr, flush=True)

def ts(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:05.2f}"

def srt_ts(t):
    t = max(0.0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"

# ---------- metadata ----------
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", SRC],
                                  capture_output=True, text=True, check=True).stdout)
DUR = float(probe["format"]["duration"])
vs = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
W, H = (int(vs["width"]), int(vs["height"])) if vs else (0, 0)
num, den = (vs["r_frame_rate"].split("/") if vs else ("0", "1"))
FPS = float(num) / float(den or 1) if vs else 0
log(f"[meta] {DUR:.1f}s {W}x{H} {FPS:.2f}fps")

# ---------- audio ----------
import librosa
SR = 22050
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
y = np.frombuffer(pcm, dtype=np.float32)
HOP = int(SR * 0.25)
rms = librosa.feature.rms(y=y, frame_length=HOP * 2, hop_length=HOP, center=True)[0]
rms_db = 20 * np.log10(np.maximum(rms, 1e-6))
t_rms = np.arange(len(rms)) * 0.25
onset = librosa.onset.onset_strength(y=y, sr=SR, hop_length=512)
t_on = librosa.frames_to_time(np.arange(len(onset)), sr=SR, hop_length=512)
tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=SR, hop_length=512)
beat_t = librosa.frames_to_time(beats, sr=SR, hop_length=512).tolist()
tempo = float(np.atleast_1d(tempo)[0])
# onset strength resampled to the 0.25 s grid
on_q = np.interp(t_rms, t_on, onset) if len(onset) else np.zeros_like(t_rms)

def norm(v):
    v = np.asarray(v, dtype=float); lo, hi = np.percentile(v, 5), np.percentile(v, 98)
    return np.clip((v - lo) / (hi - lo + 1e-9), 0, 1)

E = norm(rms_db); O = norm(on_q)
# energy rises: 2 s after vs 2 s before
k = 8
sm = np.convolve(rms_db, np.ones(4) / 4, mode="same")
rise = np.array([np.mean(sm[i:i + k]) - np.mean(sm[max(0, i - k):i]) if i >= k and i + k <= len(sm) else 0 for i in range(len(sm))])
rises = []
for i in np.argsort(-rise):
    if rise[i] < 3: break
    t = float(t_rms[i])
    if all(abs(t - r["t"]) > 6 for r in rises):
        rises.append({"t": round(t, 2), "db_jump": round(float(rise[i]), 1)})
    if len(rises) >= 5: break
silent_db = float(np.percentile(rms_db, 10))
log(f"[audio] tempo {tempo:.0f} bpm, {len(beat_t)} beats, {len(rises)} energy rises")

# integrated loudness
lufs = None
try:
    import pyloudnorm as pyln
    lufs = round(float(pyln.Meter(SR).integrated_loudness(y.astype(np.float64))), 1)
except Exception as e:
    log("[audio] loudness skipped:", e)

# ---------- scenes ----------
scenes = []
try:
    from scenedetect import detect, AdaptiveDetector
    sl = detect(SRC, AdaptiveDetector(), show_progress=False)
    scenes = [(float(s[0].seconds), float(s[1].seconds)) for s in sl]
except Exception as e:
    log("[scenes] failed:", e)
if not scenes:
    scenes = [(0.0, DUR)]
cuts = [s for s, _ in scenes[1:]]
log(f"[scenes] {len(scenes)} shots")

# ---------- picture: faces / motion / brightness per 0.5 s, keyframes + OCR ----------
import cv2
from kit_paths import MODELS
YUNET = os.path.join(MODELS, "yunet.onnx")
face_det = None

def count_faces(img):
    global face_det
    h_, w_ = img.shape[:2]
    if face_det is None:
        face_det = cv2.FaceDetectorYN.create(YUNET, "", (w_, h_), 0.7)
    face_det.setInputSize((w_, h_))
    _, f = face_det.detect(img)
    return 0 if f is None else len(f)
cap = cv2.VideoCapture(SRC)
step = 0.5
face_t, motion_t, bright_t = [], [], []
prev = None
t = 0.0
while t < DUR and vs:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    if not ok: break
    sc = 360 / max(fr.shape[:2])
    sm_fr = cv2.resize(fr, None, fx=sc, fy=sc)
    g = cv2.cvtColor(sm_fr, cv2.COLOR_BGR2GRAY)
    face_t.append(1.0 if count_faces(sm_fr) else 0.0)
    bright_t.append(float(g.mean()))
    motion_t.append(float(np.mean(cv2.absdiff(g, prev))) if prev is not None and prev.shape == g.shape else 0.0)
    prev = g
    t += step
face_t, motion_t, bright_t = map(np.array, (face_t, motion_t, bright_t))
t_pic = np.arange(len(face_t)) * step

def ocr(img_path):
    try:
        r = subprocess.run(["tesseract", img_path, "-", "--psm", "11", "tsv"], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return "", None
    words, boxes = [], []
    for line in r.splitlines()[1:]:
        p = line.split("\t")
        if len(p) < 12: continue
        try: conf = float(p[10])
        except ValueError: continue
        txt = p[11].strip()
        if conf >= 70 and len(re.sub(r"[^A-Za-z0-9]", "", txt)) >= 2:
            words.append(txt); boxes.append([int(p[6]), int(p[7]), int(p[6]) + int(p[8]), int(p[7]) + int(p[9])])
    if not words: return "", None
    b = np.array(boxes)
    return " ".join(words), [int(b[:, 0].min()), int(b[:, 1].min()), int(b[:, 2].max()), int(b[:, 3].max())]

scene_info = []
for i, (s, e) in enumerate(scenes):
    mid = s + (e - s) * 0.5
    cap.set(cv2.CAP_PROP_POS_MSEC, mid * 1000)
    ok, fr = cap.read()
    fp = os.path.join(OUT, "frames", f"scene_{i:02d}_{mid:06.2f}s.jpg")
    txt, box = ("", None)
    if ok:
        cv2.imwrite(fp, fr)
    m = (t_pic >= s) & (t_pic < e)
    scene_info.append({"i": i, "start": round(s, 2), "end": round(e, 2), "keyframe": fp if ok else None,
                       "face_share": round(float(face_t[m].mean()), 2) if m.any() else 0,
                       "motion": round(float(motion_t[m].mean()), 1) if m.any() else 0,
                       "onscreen_text": txt[:160], "text_box": box})
cap.release()

# OCR on at most 24 evenly spread keyframes (tesseract is slow), boxes scaled back to source pixels
ocr_idx = range(len(scene_info)) if len(scene_info) <= 24 else [int(j) for j in np.linspace(0, len(scene_info) - 1, 24)]
for j in ocr_idx:
    sc_ = scene_info[j]
    if not sc_["keyframe"]: continue
    im = cv2.imread(sc_["keyframe"]); f_ = 1280 / max(im.shape[:2])
    tmp = os.path.join(OUT, "frames", "_ocr.png"); cv2.imwrite(tmp, cv2.resize(im, None, fx=f_, fy=f_))
    txt, box = ocr(tmp)
    sc_["onscreen_text"] = txt[:160]; sc_["text_box"] = [int(v / f_) for v in box] if box else None

# what each shot shows (CLIP zero-shot, local) + optional --find queries
finds = {}
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import describe_frames as DF
    kps = [x["keyframe"] for x in scene_info if x["keyframe"]]
    kis = [x for x in scene_info if x["keyframe"]]
    for x, d in zip(kis, DF.describe(kps)):
        x["looks_like"] = [l for l, pr in d if pr >= 0.25] or [f"unsure ({d[0][0]}?)"]
    for q in a.find:
        sims = DF.rank(kps, q)
        order = np.argsort(sims)[::-1][:5]
        finds[q] = [{"scene": kis[j]["i"], "start": kis[j]["start"], "end": kis[j]["end"], "sim": sims[j]} for j in order]
    log(f"[frames] described {len(kps)} shots")
except Exception as e:
    log("[frames] describe skipped:", e)

# contact sheet (max 24 tiles)
try:
    from PIL import Image, ImageDraw, ImageFont
    picks = scene_info if len(scene_info) <= 24 else [scene_info[int(j)] for j in np.linspace(0, len(scene_info) - 1, 24)]
    tw = 384; th = int(tw * H / W) if W else 216
    cols = 4; rows = math.ceil(len(picks) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 34)), "black")
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception: font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    for j, sc_ in enumerate(picks):
        if not sc_["keyframe"]: continue
        im = Image.open(sc_["keyframe"]).convert("RGB").resize((tw, th))
        x, y0 = (j % cols) * tw, (j // cols) * (th + 34)
        sheet.paste(im, (x, y0 + 34))
        d.text((x + 6, y0 + 5), f"#{sc_['i']}  {ts(sc_['start'])}-{ts(sc_['end'])}", fill="yellow", font=font)
    sheet.save(os.path.join(OUT, "contact_sheet.jpg"), quality=85)
except Exception as e:
    log("[sheet] failed:", e)

# ---------- transcript ----------
segments, words, lang = [], [], None
if not a.no_transcript:
    cache = os.path.join(OUT, f"_whisper_{a.model}_{a.lang}_{int(a.speech)}.json")
if not a.no_transcript and os.path.exists(cache):
    segments, words, lang = json.load(open(cache)); log("[whisper] using cached transcript")
elif not a.no_transcript:
    from faster_whisper import WhisperModel
    log(f"[whisper] model {a.model} ...")
    model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    a16 = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, dtype=np.float32)
    segs, info = model.transcribe(a16, language=None if a.lang == "auto" else a.lang, word_timestamps=True, vad_filter=a.speech,
                                  condition_on_previous_text=False, beam_size=a.beam)
    lang = f"{info.language} ({info.language_probability:.2f})"
    for sg in segs:
        if sg.no_speech_prob > 0.7 and sg.avg_logprob < -1.0:
            continue
        ws = []
        for w in (sg.words or []):
            # drop words sitting in near-silence (whisper invents text over silence)
            i0 = int(w.start / 0.25); i1 = max(i0 + 1, int(w.end / 0.25))
            if rms_db[i0:i1].size and rms_db[i0:i1].max() < silent_db + 3 and rms_db.max() - silent_db > 20:
                continue
            tx = w.word.strip()
            if not re.sub(r"[\W_]", "", tx) or w.end - w.start > 2.5 or w.probability < 0.05:
                continue
            if a.lang in ("en", "fr", "pcm") and re.search(r"[^\x00-\x7F\u00C0-\u024F\u2018\u2019\u201C\u201D\u2026]", tx):
                continue  # junk script characters
            ws.append({"text": tx, "start": round(w.start, 2), "end": round(w.end, 2), "p": round(w.probability, 2)})
        if ws:
            segments.append({"start": ws[0]["start"], "end": ws[-1]["end"], "text": " ".join(x["text"] for x in ws),
                             "logprob": round(sg.avg_logprob, 2)})
            words.extend(ws)
    for n, w in enumerate(words):
        w["id"] = f"w{n}"
    log(f"[whisper] {len(segments)} lines, {len(words)} words, language {lang}")
    json.dump([segments, words, lang], open(cache, "w"))

# repeated lines = chorus / catchphrase. Two signals: the same line again, and lines built from the
# song's most repeated words (a chorus like "nriri, nriri now" changes slightly each time).
STOP = set("the a an and i you me my your to of in it is on for be we he she they that this oh yeah na no so do go dey".split())
def toks(x):
    return [t for t in re.sub(r"[^a-z0-9 ]", " ", x.lower()).split() if len(t) >= 2]
def key(s):
    return " ".join(toks(s)[:6])
cnt = collections.Counter(key(s["text"]) for s in segments if len(toks(s["text"])) >= 2)
tf = collections.Counter(t for s in segments for t in toks(s["text"]) if t not in STOP)
frequent = {t for t, c in tf.items() if c >= 4}
for s in segments:
    s["repeats"] = cnt.get(key(s["text"]), 1)
    tk = toks(s["text"])
    s["hook_words"] = round(sum(1 for t in tk if t in frequent) / max(1, len(tk)), 2)
    s["is_hook"] = s["repeats"] >= 2 or s["hook_words"] >= 0.4
low_conf = (np.mean([w["p"] for w in words]) if words else 0)

# ---------- suggested cuts ----------
n = len(t_rms)
speech = np.zeros(n); chorus = np.zeros(n)
for s in segments:
    i0, i1 = int(s["start"] / 0.25), int(math.ceil(s["end"] / 0.25))
    speech[i0:i1] = 1
    if s["is_hook"]: chorus[i0:i1] = 1
face_q = np.interp(t_rms, t_pic, face_t) if len(face_t) else np.zeros(n)
mot_q = norm(np.interp(t_rms, t_pic, motion_t)) if len(motion_t) else np.zeros(n)
score_q = 0.35 * E + 0.15 * O + 0.15 * speech + 0.15 * chorus + 0.12 * face_q + 0.08 * mot_q

seg_starts = [s["start"] for s in segments]; seg_ends = [s["end"] for s in segments]

def snap_start(t0):
    cands = [(abs(x - t0), 0, x) for x in seg_starts if abs(x - t0) <= 1.0] + \
            [(abs(x - t0), 1, x) for x in cuts if abs(x - t0) <= 0.75] + \
            [(abs(x - t0), 2, x) for x in beat_t if abs(x - t0) <= 0.5]
    t1 = min(cands)[2] if cands else t0
    for w in words:  # never start inside a word
        if w["start"] < t1 < w["end"]:
            t1 = w["start"]
    return max(0.0, t1)

def snap_end(t0):
    cands = [(abs(x - t0), 0, x) for x in seg_ends if abs(x - t0) <= 1.2] + \
            [(abs(x - t0), 1, x) for x in cuts if abs(x - t0) <= 0.75] + \
            [(abs(x - t0), 2, x) for x in beat_t if abs(x - t0) <= 0.5]
    t1 = min(cands)[2] if cands else t0
    for w in words:  # never end inside a word
        if w["start"] < t1 < w["end"]:
            t1 = w["end"] + 0.1
    return min(DUR, t1)

suggest = {}
for L in [float(x) for x in a.lens.split(",") if x]:
    m = int(L / 0.25)
    if m >= n: continue
    win = np.convolve(score_q, np.ones(m) / m, mode="valid")
    picks = []
    for i in np.argsort(-win):
        t0 = float(t_rms[i])
        if t0 < 0.5 and DUR > L + 5: continue  # avoid the cold open/logo
        if all(abs(t0 - p["raw"]) >= L for p in picks):
            s0 = snap_start(t0); e0 = snap_end(s0 + L)
            if not (L * 0.6 <= e0 - s0 <= L * 1.4):
                s0, e0 = t0, min(DUR, t0 + L)
            inside = [w for w in words if w["start"] >= s0 - 0.05 and w["end"] <= e0 + 0.05]
            lines = [s["text"] for s in segments if s["end"] > s0 and s["start"] < e0]
            why = []
            seg_sc = score_q[int(s0 / 0.25):int(e0 / 0.25)]
            if E[int(s0 / 0.25):int(e0 / 0.25)].mean() > 0.7: why.append("loud/high-energy")
            if any(abs(r["t"] - s0) < 2.5 for r in rises): why.append("starts on an energy rise (drop)")
            if chorus[int(s0 / 0.25):int(e0 / 0.25)].mean() > 0.4: why.append("repeated line (chorus/catchphrase)")
            if face_q[int(s0 / 0.25):int(e0 / 0.25)].mean() > 0.5: why.append("face on screen")
            if any(s0 < c < e0 for c in cuts): why.append(f"{sum(1 for c in cuts if s0 < c < e0)} shot changes")
            picks.append({"raw": t0, "start": round(s0, 2), "end": round(e0, 2), "score": round(float(seg_sc.mean()) if seg_sc.size else 0, 3),
                          "lines": lines, "why": why,
                          "words_rel": [{"id": f"w{k}", "text": w["text"], "start": round(w["start"] - s0, 2), "end": round(w["end"] - s0, 2)}
                                        for k, w in enumerate(inside)]})
        if len(picks) >= a.top: break
    suggest[f"{int(L)}s"] = picks
    for j, p in enumerate(picks, 1):
        base = os.path.join(OUT, f"cut_{int(L)}s_{j}")
        json.dump(p["words_rel"], open(base + "_words.json", "w"), indent=1)
        with open(base + ".srt", "w") as f:
            k = 1
            for s in segments:
                if s["end"] <= p["start"] or s["start"] >= p["end"]: continue
                f.write(f"{k}\n{srt_ts(max(0, s['start'] - p['start']))} --> {srt_ts(min(p['end'], s['end']) - p['start'])}\n{s['text']}\n\n"); k += 1

# hook-anchored cuts: start on the first run of chorus/hook lines (the part people know), whatever its loudness
hook_runs = []
for sg in segments:
    if sg["is_hook"]:
        if hook_runs and sg["start"] - hook_runs[-1][-1]["end"] < 2.0: hook_runs[-1].append(sg)
        else: hook_runs.append([sg])
hook_runs = [r for r in hook_runs if len(r) >= 2] or hook_runs
hook_cuts = {}
if hook_runs:
    h0 = snap_start(hook_runs[0][0]["start"])
    for L in [float(x) for x in a.lens.split(",") if x]:
        e0 = snap_end(h0 + L)
        if not (L * 0.6 <= e0 - h0 <= L * 1.4): e0 = min(DUR, h0 + L)
        inside = [w for w in words if w["start"] >= h0 - 0.05 and w["end"] <= e0 + 0.05]
        hook_cuts[f"{int(L)}s"] = {"start": round(h0, 2), "end": round(e0, 2),
                                    "lines": [x["text"] for x in segments if x["end"] > h0 and x["start"] < e0]}
        base = os.path.join(OUT, f"cut_{int(L)}s_hook")
        json.dump([{"id": f"w{k}", "text": w["text"], "start": round(w["start"] - h0, 2), "end": round(w["end"] - h0, 2)} for k, w in enumerate(inside)],
                  open(base + "_words.json", "w"), indent=1)
        with open(base + ".srt", "w") as f:
            k = 1
            for x in segments:
                if x["end"] <= h0 or x["start"] >= e0: continue
                f.write(f"{k}\n{srt_ts(max(0, x['start'] - h0))} --> {srt_ts(min(e0, x['end']) - h0)}\n{x['text']}\n\n"); k += 1

# ---------- caption placement ----------
boxes = [s["text_box"] for s in scene_info if s["text_box"]]
text_zone = None
if boxes and H:
    ys = [((b[1] + b[3]) / 2) / H for b in boxes]
    text_zone = "top" if np.median(ys) < 0.35 else ("bottom" if np.median(ys) > 0.65 else "middle")
placement = {
    "source_has_burned_text": bool(boxes), "source_text_zone": text_zone,
    "advice": ("Source already shows its own text (" + (text_zone or "?") + "): crop/scale so it is out of frame or put my captions in a different zone. " if boxes else "") +
              "Vertical 1080x1920: every word inside y 168-1330 px, nothing under the right action rail (x > 900); "
              "captions at the bottom of that band (~y 1150-1300), never over a face; 2-3 words per group for music/high energy, "
              "3-5 for talk; first caption 0.1-0.3 s after the cut starts.",
}

# ---------- write ----------
res = {"source": SRC, "duration": round(DUR, 2), "size": [W, H], "fps": round(FPS, 2), "language": lang,
       "tempo_bpm": round(tempo, 1), "integrated_lufs": lufs, "energy_rises": rises, "shot_changes": [round(c, 2) for c in cuts],
       "scenes": scene_info, "segments": segments, "word_count": len(words), "mean_word_confidence": round(float(low_conf), 2),
       "suggested_cuts": {k: [{x: y for x, y in p.items() if x not in ("raw", "words_rel")} for p in v] for k, v in suggest.items()},
       "hook_cuts": hook_cuts, "find": finds, "caption_placement": placement,
       "loudness_per_second_db": [round(float(np.mean(rms_db[i:i + 4])), 1) for i in range(0, n, 4)]}
json.dump(res, open(os.path.join(OUT, "timeline.json"), "w"), indent=1)
json.dump([{k: w[k] for k in ("id", "text", "start", "end")} for w in words], open(os.path.join(OUT, "words.json"), "w"), indent=1)
with open(os.path.join(OUT, "transcript.srt"), "w") as f:
    for i, s in enumerate(segments, 1):
        f.write(f"{i}\n{srt_ts(s['start'])} --> {srt_ts(s['end'])}\n{s['text']}\n\n")

L_ = []
L_.append(f"# Source analysis: {os.path.basename(SRC)}")
L_.append(f"{DUR:.1f}s, {W}x{H}, {FPS:.0f} fps, tempo {tempo:.0f} bpm, loudness {lufs} LUFS, language {lang}, "
          f"{len(scenes)} shots, {len(words)} words (mean confidence {low_conf:.2f}{' - LOW, check lyrics by ear/official source' if words and low_conf < 0.6 else ''})")
L_.append("\n## Best hook moments (biggest energy rises)")
for r in rises: L_.append(f"- {ts(r['t'])}  +{r['db_jump']} dB")
L_.append("\n## Suggested cut ranges")
for k, v in suggest.items():
    for j, p in enumerate(v, 1):
        L_.append(f"- {k} #{j}: {ts(p['start'])} -> {ts(p['end'])}  score {p['score']}  [{', '.join(p['why']) or 'balanced'}]  files cut_{k}_{j}.srt/_words.json")
        for ln in p["lines"][:3]: L_.append(f"    \"{ln}\"")
L_.append("\n## Chorus / hook cuts (start on the first repeated hook line)")
for k, v in hook_cuts.items():
    L_.append(f"- {k}: {ts(v['start'])} -> {ts(v['end'])}  files cut_{k}_hook.srt/_words.json")
    for ln in v["lines"][:3]: L_.append(f"    \"{ln}\"")
L_.append("\n## Transcript (timed)")
for s in segments: L_.append(f"- {ts(s['start'])}-{ts(s['end'])}{'  [HOOK/chorus]' if s['is_hook'] else ''}  {s['text']}")
L_.append("\n## Shots")
for s in scene_info:
    L_.append(f"- #{s['i']} {ts(s['start'])}-{ts(s['end'])} {', '.join(s.get('looks_like', []))} | face {int(s['face_share'] * 100)}% motion {s['motion']}" +
              (f"  text: \"{s['onscreen_text'][:70]}\" at {s['text_box']}" if s['onscreen_text'] else ""))
if finds:
    L_.append("\n## Moments you asked me to find (best matching shots)")
    for q, v in finds.items():
        L_.append(f"- \"{q}\": " + ", ".join(f"#{x['scene']} {ts(x['start'])}-{ts(x['end'])} ({x['sim']})" for x in v))
L_.append("\n## Captions\n" + placement["advice"])
L_.append("\nShot labels are CLIP guesses: before using a shot as proof (the ring, the kiss), look at its keyframe in frames/.")
open(os.path.join(OUT, "timeline.md"), "w").write("\n".join(L_) + "\n")
print(os.path.join(OUT, "timeline.md"))
