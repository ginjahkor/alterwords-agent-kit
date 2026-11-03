#!/usr/bin/env python3
"""Say what is on screen in video frames, locally and free (CLIP ViT-B/32, ONNX, CPU).

Zero-shot: each frame is scored against a list of plain-English shot descriptions and the best two
are returned. Good enough to know WHICH shots show the artist singing, the couple, the ring, a crowd,
lyrics text, a car, etc., so I can pick the right range. It does not read text (OCR does that in
analyze_source.py) and it can be wrong on unusual shots: confirm the chosen shot by looking at the frame.

Usage: describe_frames.py FRAME.jpg [FRAME2.jpg ...] [--labels "a,b,c"]
As a module: from describe_frames import describe; describe([paths]) -> [[(label, prob), ...], ...]
"""
import os, sys, json, numpy as np

REPO = "Xenova/clip-vit-base-patch32"
LABELS = [
    "a singer performing to the camera", "a man and a woman together, romantic", "a man kneeling with an engagement ring",
    "a wedding or engagement ceremony", "a close-up of a face", "a group of people dancing", "a crowd at a concert",
    "a big party or celebration", "lyrics or words written on screen", "a title card or logo", "a person driving or a car",
    "a city street", "a house interior or living room", "a beach or the sea", "a nightclub with colorful lights",
    "a footballer or a football match", "a news studio or presenter", "a person talking in an interview or podcast",
    "money or cash", "a phone screen or social media post", "food or cooking",
    "nature, trees or fields", "a luxury car or jewelry", "a baby or children",
]
_S = {}

def _load():
    if _S: return _S
    import onnxruntime as ort
    from tokenizers import Tokenizer
    from huggingface_hub import hf_hub_download
    o = ort.SessionOptions(); o.intra_op_num_threads = os.cpu_count() or 4
    _S["v"] = ort.InferenceSession(hf_hub_download(REPO, "onnx/vision_model_quantized.onnx"), o, providers=["CPUExecutionProvider"])
    _S["t"] = ort.InferenceSession(hf_hub_download(REPO, "onnx/text_model_quantized.onnx"), o, providers=["CPUExecutionProvider"])
    tok = Tokenizer.from_file(hf_hub_download(REPO, "tokenizer.json"))
    tok.enable_padding(length=77, pad_id=49407); tok.enable_truncation(77)
    _S["tok"] = tok
    return _S

def _text_emb(labels):
    s = _load()
    enc = s["tok"].encode_batch([f"a photo of {l}" for l in labels])
    ids = np.array([e.ids for e in enc], dtype=np.int64); am = np.array([e.attention_mask for e in enc], dtype=np.int64)
    feeds = {}
    for i in s["t"].get_inputs():
        feeds[i.name] = ids if "input_ids" in i.name else am
    out = s["t"].run(None, feeds)
    names = [o.name for o in s["t"].get_outputs()]
    e = out[names.index("text_embeds")] if "text_embeds" in names else out[0]
    return e / np.linalg.norm(e, axis=1, keepdims=True)

def _img(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    g = np.asarray(im.convert("L"), dtype=np.float32)
    rows = np.where(g.mean(1) > 18)[0]; cols = np.where(g.mean(0) > 18)[0]
    if len(rows) > g.shape[0] * 0.3 and len(cols) > g.shape[1] * 0.3:  # cut letterbox / pillarbox bars
        im = im.crop((int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1))
    w, h = im.size; sc = 224 / min(w, h)
    im = im.resize((max(224, round(w * sc)), max(224, round(h * sc))), Image.BICUBIC)
    w, h = im.size; l, t = (w - 224) // 2, (h - 224) // 2
    x = np.asarray(im.crop((l, t, l + 224, t + 224)), dtype=np.float32) / 255.0
    x = (x - np.array([0.48145466, 0.4578275, 0.40821073])) / np.array([0.26862954, 0.26130258, 0.27577711])
    return x.transpose(2, 0, 1).astype(np.float32)

def describe(paths, labels=None, top=2):
    labels = labels or LABELS
    s = _load(); T = _text_emb(labels)
    res = []
    for i in range(0, len(paths), 16):
        batch = np.stack([_img(p) for p in paths[i:i + 16]])
        out = s["v"].run(None, {s["v"].get_inputs()[0].name: batch})
        names = [o.name for o in s["v"].get_outputs()]
        e = out[names.index("image_embeds")] if "image_embeds" in names else out[0]
        e = e / np.linalg.norm(e, axis=1, keepdims=True)
        logits = 100.0 * e @ T.T
        pr = np.exp(logits - logits.max(1, keepdims=True)); pr /= pr.sum(1, keepdims=True)
        for row in pr:
            idx = np.argsort(-row)[:top]
            res.append([(labels[j], round(float(row[j]), 2)) for j in idx])
    return res

def rank(paths, query):
    """Cosine similarity of each frame to one description (higher = closer). Use to FIND a moment, e.g. the ring."""
    s = _load(); T = _text_emb([query])[0]
    sims = []
    for i in range(0, len(paths), 16):
        batch = np.stack([_img(p) for p in paths[i:i + 16]])
        out = s["v"].run(None, {s["v"].get_inputs()[0].name: batch})
        names = [o.name for o in s["v"].get_outputs()]
        e = out[names.index("image_embeds")] if "image_embeds" in names else out[0]
        e = e / np.linalg.norm(e, axis=1, keepdims=True)
        sims.extend((e @ T).tolist())
    return [round(float(x), 3) for x in sims]

if __name__ == "__main__":
    args = sys.argv[1:]; labels = None
    if "--labels" in args:
        k = args.index("--labels"); labels = [x.strip() for x in args[k + 1].split(",")]; args = args[:k] + args[k + 2:]
    for p, d in zip(args, describe(args, labels)):
        print(os.path.basename(p), "->", "; ".join(f"{l} ({pr:.2f})" for l, pr in d))
