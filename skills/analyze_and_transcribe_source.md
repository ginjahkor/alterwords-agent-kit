# Skill: Analyze and transcribe a source video

Use this on ANY clip before you cut it (YouTube download, X/TikTok clip, and your own rendered talking head for
caption timing). It runs locally for free on CPU. No avatar credits, no paid APIs.

## Files
- `scripts/analyze_source.py`: the analyzer.
- `scripts/describe_frames.py`: says what is in a frame (CLIP ViT-B/32 ONNX, model Xenova/clip-vit-base-patch32,
  cached in ~/.cache/huggingface). Also usable alone.
- Guide: `rules/SOURCE_ANALYSIS_AND_EDIT_TOOLS.md`

## Run
`cd <kit> && . scripts/env.sh`
- Song / music video (default music mode, keeps singing):
  `python3 scripts/analyze_source.py $AGENT_WORK/NAME/NAME.mp4 --out $AGENT_WORK/NAME/analysis`
- Interview, podcast, trailer, news, your own talking head (VAD on):
  `python3 scripts/analyze_source.py SRC.mp4 --out DIR --speech`
- Find a specific moment: add `--find "a man kneeling with a ring"` (repeatable).
- Other flags: `--lens 4,6,10` (cut lengths in s), `--top 3` (suggestions per length), `--model small` (default;
  `base` is faster and worse), `--lang en` (default; good for Nigerian English/pidgin; `auto` mis-detects pidgin as
  Yoruba and returns junk), `--no-transcript` (pictures/audio only), `--beam 2`.
- Time: about 3 minutes for a 3.5-minute song, about 2 minutes for a 2-minute talk clip. Run it with `timeout 580` or in
  the background (`setsid nohup ... > DIR/analyze.log 2>&1 &`) for long sources. The transcript is cached
  (_whisper_*.json) so a rerun is fast.

## Outputs (read timeline.md first)
- `timeline.md`: transcript lines with times, chorus/hook lines (repeated lyric lines), every shot with a CLIP label +
  face share, on-screen text with WHERE it sits, loudness build-ups (energy rises = drops / chorus entries), the --find
  matches, and suggested cut ranges per length with reasons.
- `timeline.json`: the same, machine-readable.
- `words.json`: every word `{id,text,start,end}` in SOURCE seconds (HyperFrames caption format; use with
  `hf_build.py --words-abs`).
- `transcript.srt`: full subtitles.
- `cut_<len>s_<n>.srt` + `cut_<len>s_<n>_words.json`, `cut_<len>s_hook.*`: each suggested cut, times RELATIVE to the cut
  start, snapped so a cut never starts or ends mid-word (prefers line starts, beats and shot changes).
- `contact_sheet.jpg` + `frames/`: one keyframe per shot with its timestamp. LOOK at the contact sheet to confirm the shot
  you pick really shows what you think.

## How to choose the cut
1. For songs, the trending part is usually the hook/chorus line or the biggest energy rise. For talk, the line that
   carries the story (the quote, the announcement, the punchline).
2. Pick a suggested cut (or set your own start/end on word boundaries from words.json). Keep inserted clips 4 to 7 s.
3. Check on-screen text positions so your headline/captions don't cover the video's own text or logo.
4. Check the shot at the cut with the keyframe (it must show the right moment).

## Accuracy rules (important)
- Whisper hears SINGING badly and mishears names. For songs, the WORDS come from the official lyrics or the video's own
  on-screen lyrics; only the TIMING comes from the tool. Fix words with `hf_build.py --replace "Wrong=Right"`.
- For your own captions, the words come from your script.txt (`hf_build.py --script-file`); whisper only gives timing.
- Never state a fact in a video only because the transcript seemed to say it. Confirm names and numbers in a written
  source.
- CLIP labels are guesses. Confirm with the frame.

## Known failures and fixes
- Empty/garbage transcript on pidgin: keep `--lang en`; for a song with little clear singing, use `--no-transcript` and
  time by energy rises + shot changes.
- Words invented over silence are dropped automatically; if odd words remain in an intro, ignore them.
- Very long source (podcast > 20 min): cut a section first (download_youtube.sh SECTION or ffmpeg -ss/-to) and analyze
  that.
- Out of memory / slow: `--model base`.
- tesseract missing text on stylised fonts: read the frame yourself.

## Reinstall
`bash install.sh`, then `bash selftest.sh`. Whisper models download themselves the first time into
~/.cache/huggingface (Systran/faster-whisper-small, -base); CLIP downloads the first time describe_frames.py runs.

## Report
Name the line/moment you chose and why (hook, chorus, announcement), its time range in the source, and anything the
tool got wrong that you corrected.
