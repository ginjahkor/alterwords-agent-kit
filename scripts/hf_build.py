#!/usr/bin/env python3
"""Build and render a produced-looking vertical segment with HyperFrames (free, local, no HeyGen).

Two layouts:
  card : the source clip (16:9 music video, interview) sits in a rounded card over a blurred,
         darkened copy of itself, title on top, word-by-word captions under the card.
  full : a vertical clip (my HeyGen talking head, a TikTok) fills the frame, word-by-word
         captions in the lower safe band (use it to caption MY OWN voice).

Captions come from analyze_source.py word files (cut_*_words.json, words.json; times in seconds).
Each word pops in on its own timestamp and turns yellow while it is said/sung.

Usage:
  hf_build.py --clip SRC.mp4 --start 48.24 --end 55.24 --words cut_6s_hook_words.json --word-offset 0.3 \
     --layout card --pill "NEW MUSIC" --title "DAVIDO" --subtitle "ALREADY FALLING" \
     --credit "Clip: OWNER NAME, official video (YouTube)" --out /path/seg.mp4
  --words-abs   the word file uses SOURCE times (words.json): they are shifted by -start automatically
  --max-words 3 words per caption group (2-3 music/energy, 3-5 talk)
  --mute        drop the clip's audio (e.g. I add my own voice/mix later in FFmpeg)
Render: about 7 s of video per 45-50 s on this VM. Output 1080x1920 H.264/AAC 30 fps.
RULE: never run `hyperframes auth login` or any heygen recipe from HyperFrames' media-use skill
(that spends HeyGen credits). Free/local paths only.
"""
import argparse, html, json, os, re, shutil, subprocess, sys
from kit_paths import setting  # colours, fonts and caption style come from settings.env

ap = argparse.ArgumentParser()
ap.add_argument("--clip", required=True)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float)
ap.add_argument("--words")
ap.add_argument("--words-abs", action="store_true")
ap.add_argument("--word-offset", type=float, default=0.0, help="seconds added to every word time")
ap.add_argument("--layout", choices=["card", "full"], default="card")
ap.add_argument("--pill", default="")
ap.add_argument("--title", default="")
ap.add_argument("--subtitle", default="")
ap.add_argument("--credit", default="")
ap.add_argument("--max-words", type=int, default=3)
ap.add_argument("--accent", default=setting("AGENT_ACCENT", "#ffd400"))
ap.add_argument("--caption-style", choices=["word", "line"], default=setting("AGENT_CAPTION_STYLE", "word"),
                help="word = each word lights up in the accent colour as it is said; line = plain captions")
ap.add_argument("--mute", action="store_true")
ap.add_argument("--script-file", help="the exact words spoken (the HeyGen script or the voiceover script): caption TEXT comes from it, TIMING from whisper")
ap.add_argument("--replace", action="append", default=[], help='fix a misheard word: --replace "Iriri=Nriri" (check lyrics against the on-screen text/official lyrics)')
ap.add_argument("--out", required=True)
ap.add_argument("--no-render", action="store_true", help="only write the HyperFrames project (index.html + assets); do not render")
ap.add_argument("--project", help="project dir (default next to --out)")
a = ap.parse_args()

HF = os.path.join(subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True).stdout.strip(), "bin", "hyperframes")
ENV = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", DO_NOT_TRACK="1", HYPERFRAMES_SKIP_SKILLS="1")
src = os.path.abspath(a.clip)
dur_src = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                               capture_output=True, text=True).stdout)
end = a.end if a.end else dur_src
D = round(end - a.start, 2)
proj = os.path.abspath(a.project or os.path.splitext(os.path.abspath(a.out))[0] + "_hf")
if os.path.exists(proj): shutil.rmtree(proj)
os.makedirs(os.path.join(proj, "assets"))

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)

aud = ["-an"] if a.mute else ["-c:a", "aac", "-b:a", "192k"]
if a.layout == "card":
    ff("-ss", str(a.start), "-t", str(D), "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", *aud, os.path.join(proj, "assets", "fg.mp4"))
    ff("-ss", str(a.start), "-t", str(D), "-i", src, "-an", "-vf", "scale=-2:1920,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", os.path.join(proj, "assets", "bg.mp4"))
else:
    ff("-ss", str(a.start), "-t", str(D), "-i", src, "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", *aud, os.path.join(proj, "assets", "fg.mp4"))

# ---- words -> groups ----
words = []
if a.words:
    for w in json.load(open(a.words)):
        s, e = w["start"], w["end"]
        if a.words_abs: s, e = s - a.start, e - a.start
        s, e = s + a.word_offset, e + a.word_offset
        t = re.sub(r"^[^\w']+|[^\w'?!]+$", "", w["text"])
        for rp in a.replace:
            old, new = rp.split("=", 1)
            if t.lower() == old.lower(): t = new
        if t and e > 0.05 and s < D - 0.1 and t.lower() not in ("mm", "hmm", "uh", "um"):
            words.append([max(0.0, s), min(D, e), t])
if a.script_file and words:
    import difflib
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    sc = [t for t in re.sub(r"\s+", " ", open(a.script_file).read()).split(" ") if norm(t)]
    sw = [norm(w[2]) for w in words]
    m = difflib.SequenceMatcher(None, sw, [norm(t) for t in sc], autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in m.get_opcodes():
        if op == "equal":
            out += [[words[i1 + k][0], words[i1 + k][1], sc[j1 + k]] for k in range(i2 - i1)]
        elif op in ("replace", "insert") and j2 > j1:
            if i2 > i1: t0, t1 = words[i1][0], words[i2 - 1][1]
            else:
                t0 = out[-1][1] if out else 0.0
                t1 = words[i1][0] if i1 < len(words) else min(D, t0 + 0.3 * (j2 - j1))
            st = (t1 - t0) / (j2 - j1)
            out += [[t0 + k * st, t0 + (k + 1) * st, sc[j1 + k]] for k in range(j2 - j1)]
        # "delete": whisper heard words that are not in the script -> drop
    # keep only script words inside this segment's time range
    words = [[round(s_, 2), round(e_, 2), re.sub(r"^[^\w']+|[^\w'?!]+$", "", t)] for s_, e_, t in out if e_ > 0.05 and s_ < D - 0.1]

groups = []
for i, w in enumerate(words):
    brk = (not groups or len(groups[-1]) >= a.max_words or w[0] - groups[-1][-1][1] > 0.35
           or re.search(r"[.?!,]$", words[i - 1][2] if i else ""))
    (groups.append([w]) if brk else groups[-1].append(w))

cap_top = 1090 if a.layout == "card" else 1120
if a.layout == "full" and setting("AGENT_CAPTION_POSITION", "lower") == "middle":
    cap_top = 860  # face fills the lower third: captions sit mid-frame
cap_html, W, G = [], [], []
k = 0
for gi, g in enumerate(groups):
    gs = max(0.0, g[0][0] - 0.05)
    ge = groups[gi + 1][0][0] - 0.05 if gi + 1 < len(groups) else min(D, g[-1][1] + 0.6)
    ge = max(ge, gs + 0.3)
    spans = []
    for j, w in enumerate(g):
        if j and len(" ".join(x[2] for x in g)) > 14 and j == len(g) - 1:
            spans.append("<br />")
        spans.append(f'<span class="w" id="w{k}">{html.escape(w[2])}</span>')
        W.append([round(w[0], 2), round(w[1], 2)]); k += 1
    cap_html.append(f'      <div id="g{gi}" class="cap clip" data-start="{gs:.2f}" data-duration="{ge - gs:.2f}" data-track-index="3">{"".join(spans)}</div>')
    G.append([f"#g{gi}", round(gs, 2), round(ge, 2)])

head = ""
if a.pill or a.title:
    head = ('      <div id="head" class="clip" data-start="0" data-duration="%s" data-track-index="2">' % D +
            (f'<div id="pill">{html.escape(a.pill)}</div>' if a.pill else "") +
            (f'<div id="title">{html.escape(a.title)}' + (f'<br /><span>{html.escape(a.subtitle)}</span>' if a.subtitle else "") + "</div>" if a.title else "") +
            "</div>")
has_audio = "false" if a.mute else "true"
if a.layout == "card":
    media = f'''      <video id="bg" class="clip" src="assets/bg.mp4" muted playsinline data-start="0" data-duration="{D}" data-track-index="0"></video>
      <div id="shade"></div>
      <div id="fgwrap"><video id="fg" class="clip" src="assets/fg.mp4" playsinline {'muted ' if a.mute else ''}data-has-audio="{has_audio}" data-start="0" data-duration="{D}" data-track-index="1"></video></div>
      <div id="bar"><div id="barfill"></div></div>'''
else:
    media = f'''      <video id="fg" class="clip full" src="assets/fg.mp4" playsinline {'muted ' if a.mute else ''}data-has-audio="{has_audio}" data-start="0" data-duration="{D}" data-track-index="1"></video>
      <div id="shade"></div>'''
credit = f'      <div id="credit" class="clip" data-start="0" data-duration="{D}" data-track-index="4">{html.escape(a.credit)}</div>' if a.credit else ""

INK = setting("AGENT_INK", "#ffffff")
CSS = """
      :root { --ink: INK; --accent: ACCENT; --font-display: "FDISPLAY", sans-serif; --font-body: "FBODY", sans-serif; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: BGCOL; }
      #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; }
      #bg { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; z-index: 1; }
      #fg.full { position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; z-index: 1; }
      #shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.1) 30%, rgba(0,0,0,0.1) 50%, rgba(0,0,0,0.6) 75%, rgba(0,0,0,0.75) 100%); z-index: 2; }
      #fgwrap { position: absolute; left: 40px; top: 430px; width: 1000px; height: 563px; border-radius: 30px; overflow: hidden; box-shadow: 0 30px 80px rgba(0,0,0,0.6); outline: 5px solid rgba(255,255,255,0.9); z-index: 3; }
      #fgwrap #fg { width: 1000px; height: 563px; object-fit: cover; }
      #head { position: absolute; left: 0; top: 190px; width: 1080px; text-align: center; z-index: 5; }
      #pill { display: inline-block; background: var(--accent); color: #111; font-family: var(--font-body); font-weight: 800; font-size: 34px; letter-spacing: 0.12em; padding: 10px 26px; border-radius: 999px; }
      #title { margin-top: 22px; color: var(--ink); font-family: var(--font-display); font-size: 74px; line-height: 1.02; text-shadow: 0 6px 24px rgba(0,0,0,0.6); }
      #title span { color: var(--accent); }
      .cap { position: absolute; left: 60px; top: CAPTOPpx; width: 960px; text-align: center; z-index: 6; overflow: visible; }
      .cap .w { display: inline-block; font-family: var(--font-display); font-size: 100px; line-height: 1.05; color: var(--ink); margin: 0 12px; text-transform: uppercase; text-shadow: 0 8px 0 rgba(0,0,0,0.55), 0 0 30px rgba(0,0,0,0.5); }
      #credit { position: absolute; left: 0; top: 1280px; width: 1080px; text-align: center; z-index: 6; color: rgba(255,255,255,0.8); font-family: var(--font-body); font-weight: 600; font-size: 28px; }
      #bar { position: absolute; left: 40px; top: 1010px; width: 1000px; height: 8px; border-radius: 8px; background: rgba(255,255,255,0.25); z-index: 5; overflow: hidden; }
      #barfill { width: 1000px; height: 8px; background: var(--accent); transform-origin: 0 50%; }
""".replace("ACCENT", a.accent).replace("CAPTOP", str(cap_top)).replace("INK", INK).replace("BGCOL", setting("AGENT_BG", "#0b0b0f")) \
     .replace("FDISPLAY", setting("AGENT_FONT_DISPLAY", "Archivo Black")).replace("FBODY", setting("AGENT_FONT_BODY", "Montserrat"))
if a.layout == "full":
    CSS = CSS.replace("top: 1280px; width: 1080px; text-align: center", "top: 1290px; width: 1080px; text-align: center")

JS = f"""
      const D = {D};
      const tl = gsap.timeline({{ paused: true }});
      if (document.querySelector("#pill")) tl.from("#pill", {{ y: -60, opacity: 0, duration: 0.45, ease: "back.out(2)" }}, 0.05);
      if (document.querySelector("#title")) tl.from("#title", {{ y: 50, opacity: 0, duration: 0.5, ease: "power3.out" }}, 0.18);
      if (document.querySelector("#fgwrap")) {{
        tl.from("#fgwrap", {{ y: 120, opacity: 0, scale: 0.92, duration: 0.55, ease: "power3.out" }}, 0);
        tl.to("#fgwrap #fg", {{ scale: 1.08, duration: D, ease: "none" }}, 0);
        tl.fromTo("#barfill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: D, ease: "none" }}, 0);
      }} else {{
        tl.fromTo("#fg", {{ scale: 1.0 }}, {{ scale: 1.05, duration: D, ease: "none" }}, 0);
      }}
      if (document.querySelector("#credit")) tl.from("#credit", {{ opacity: 0, duration: 0.4 }}, 0.6);
      const HL = {"true" if a.caption_style == "word" else "false"};
      const W = {json.dumps(W)};
      const G = {json.dumps(G)};
      W.forEach(([s, e], i) => {{
        const id = "#w" + i;
        tl.fromTo(id, {{ scale: 0.55, opacity: 0, y: 30 }}, {{ scale: 1, opacity: 1, y: 0, duration: 0.16, ease: "back.out(3)" }}, Math.max(0, s - 0.05));
        if (HL) {{
          tl.to(id, {{ color: "{a.accent}", scale: 1.12, duration: 0.08, ease: "power2.out" }}, s);
          tl.to(id, {{ color: "{INK}", scale: 1, duration: 0.12, ease: "power2.in" }}, Math.max(s + 0.1, e - 0.06));
        }}
      }});
      G.forEach(([g, s, e]) => {{
        tl.to(g, {{ opacity: 0, duration: 0.1, ease: "power2.in" }}, Math.max(s, e - 0.1));
        tl.set(g, {{ opacity: 0 }}, e);
      }});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = tl;
      tl.seek(0);
"""

HTML = f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>{CSS}    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="1080" data-height="1920">
{media}
{head}
{chr(10).join(cap_html)}
{credit}
    </div>
    <script>{JS}    </script>
  </body>
</html>
"""
open(os.path.join(proj, "index.html"), "w").write(HTML)
open(os.path.join(proj, "hyperframes.json"), "w").write(json.dumps({
    "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
    "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    "media": {"autoProxy": True}}, indent=2))
if a.no_render:
    print(f"project written: {proj} (not rendered)"); sys.exit(0)
lint = subprocess.run([HF, "lint"], cwd=proj, env=ENV, capture_output=True, text=True)
print("\n".join(l for l in (lint.stdout + lint.stderr).splitlines() if "error" in l.lower() or "✗" in l)[:2000])
r = subprocess.run([HF, "render", "-o", os.path.abspath(a.out), "--quality", "delivery", "--fps", "30"], cwd=proj, env=ENV, capture_output=True, text=True)
if r.returncode or not os.path.exists(a.out):
    print((r.stdout + r.stderr)[-3000:], file=sys.stderr); sys.exit(1)
print(f"rendered {a.out} ({D}s, {len(groups)} caption groups, {len(W)} words)")
