# Skill: HyperFrames edit

HyperFrames (HeyGen's open-source HTML-to-video renderer, github.com/heygen-com/hyperframes) runs LOCALLY for free. It
turns a cut into a produced edit: the source clip in a rounded card over a blurred copy of itself, a pill + title, a
progress bar, and captions that pop in word by word and turn yellow while each word is said or sung. FFmpeg then
stitches the segments, adds an optional small face window, mixes audio and normalises loudness.

Agents without an avatar use the card layout with their voiceover as the audio and captions (see
PRODUCTION_GUIDE.md). Agents with an avatar can also use the full layout for their talking head.

## RULE: credits stay at zero here
- NEVER run `hyperframes auth login`, never use the heygen/TTS/avatar recipes from HyperFrames' media-use skill, never
  pass a HeyGen API key to HyperFrames. Those spend credits.
- hf_build.py sets HYPERFRAMES_NO_TELEMETRY=1, DO_NOT_TRACK=1, HYPERFRAMES_SKIP_SKILLS=1.

## Files
- `scripts/hf_build.py`: builds one segment (project folder + HTML + GSAP timeline), lints it, renders it. Read its
  header for usage.
- `templates/`: what each layout looks like and where everything sits.
- Project folders are made next to --out (e.g. POSTDIR/hf/<name>_hf/).
- CLI: hyperframes installed globally with npm (`$(npm prefix -g)/bin/hyperframes`; it is NOT on PATH, hf_build.py finds
  it). Chrome for rendering lives in ~/.cache/hyperframes/chrome.

## The two layouts (1080x1920, 30 fps, H.264/AAC)
- `--layout card`: a 16:9 source (music video, interview, trailer, or a 1280x720 still turned into a video) sits in a
  1000x563 card at y=430 with a white outline, over a blurred dark copy. Pill + title (+subtitle) at y=190. Progress bar
  at y=1010. Captions start at y=1090 (100 px font, can wrap to 2 lines, about to y=1310). Credit line at y=1280-1290.
  Free space for an optional face window: x 746-1054, y 1346-1887 (308x541 incl. white border).
- `--layout full`: a vertical clip (a talking head) fills the frame; captions start at y=1120. Keep the face ABOVE
  y=1050: punch in on the face first (crop with FFmpeg) so it sits around y 200-950. Don't use --title on full layout if
  it would sit on the forehead (title area starts y=190).

## Commands
`cd <kit> && . scripts/env.sh`
- Source clip in a card with ITS OWN sound and lyric/quote captions (words from the analyzer, source times):
  `python3 scripts/hf_build.py --clip $AGENT_WORK/NAME/NAME.mp4 --start 123.9 --end 128.3 --words $AGENT_WORK/NAME/analysis/words.json --words-abs --pill "NOLLYWOOD" --title "NO ONE FIGHTS ALONE" --subtitle "DECEMBER FILM" --credit "Clip: <channel> (YouTube)" --out POSTDIR/hf/insert.mp4`
  or use a suggested cut: `--words $AGENT_WORK/NAME/analysis/cut_6s_hook_words.json` (already relative, no --words-abs).
- A card under YOUR voice (clip muted, your words as captions): make a word file for that stretch of your voice with
  times relative to the segment start (see "Word files"), then
  `python3 scripts/hf_build.py --clip SRC --start S --end E --words POSTDIR/an/w_cardA.json --mute --pill ... --title ... --credit ... --out POSTDIR/hf/cardA.mp4`
  Card length = length of that stretch of your voice.
- A photo card: turn the picture into a 1280x720 video first, e.g.
  `ffmpeg -loop 1 -i photo.jpg -t 12 -vf "scale=1280:720,zoompan=z='min(zoom+0.0006,1.06)':d=1:s=1280x720:fps=30,format=yuv420p" -c:v libx264 -crf 18 photo.mp4`
  then use it as --clip with --start 0 --end <len> --mute.
- A talking head captioned (avatar agents):
  `ffmpeg -i POSTDIR/raw.mp4 -vf "crop=CW:CH:CX:CY,scale=1080:1920:flags=lanczos,setsar=1" -c:v libx264 -crf 16 -c:a aac -b:a 192k POSTDIR/me_punch.mp4`
  (CH = CW*16/9, face roughly centred, hands out where possible)
  `python3 scripts/hf_build.py --clip POSTDIR/me_punch.mp4 --layout full --words POSTDIR/an/words_fixed.json --out POSTDIR/hf/me_full.mp4`
- Options: `--max-words 3` (2-3 for music/energy, 3-5 for talk), `--accent "#ffd400"`, `--word-offset 0.3` (shift
  captions), `--replace "Wrong=Right"` (fix a misheard word), `--script-file POSTDIR/script.txt` (caption text from your
  script, timing from whisper).
- Render time: about 7 s of video per 45-50 s; a 32 s captioned talking head took 3 min 20 s. Run long renders with
  `timeout 580` or in the background.

## Word files (captions must say exactly what is said)
- Your voice (voiceover or avatar): run "Analyze and transcribe a source video" on the audio/video with `--speech` to get
  POSTDIR/an/words.json, then fix names/pidgin against script.txt into words_fixed.json. For each card stretch [a,b)
  keep words starting inside it, subtract a, renumber ids (w0, w1...).
- Songs: lyric words from official/on-screen lyrics, timing from the tool.

## Assembling the finished video (FFmpeg, after the HyperFrames segments)
1. Base = your voice track with captions (voiceover over cards, or the captioned talking head). Overlay each card at its
   time with `setpts=PTS-STARTPTS+T/TB` and `overlay=0:0:eof_action=pass:enable='between(t,A,B)'`.
2. Optional (avatar agents): on every card stretch, overlay the face window: me_punch.mp4 trimmed the same way,
   `scale=300:533,pad=308:541:4:4:white`, at `overlay=746:1346`.
3. A source clip with its own sound is a separate segment inserted between sentences (cut at a sentence end):
   segA = voice 0..cut, segB = insert.mp4, segC = voice cut..end.
4. Match levels: measure each part with `ffmpeg -i X -af ebur128 -f null -` and turn the clip down/up to within about
   1-2 LU of your voice (e.g. clip -11.7 vs voice -16.4, so -4.5 dB).
5. Concat + loudness: `ffmpeg -i segA.mp4 -i segB.mp4 -i segC.mp4 -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a];[a]loudnorm=I=-14:TP=-1.5:LRA=11[an]" -map "[v]" -map "[an]" -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart -c:a aac -ar 48000 -b:a 192k final.mp4`
6. Chat copy if final.mp4 is over 10 MB: re-encode at `-b:v 1900k -maxrate 2200k -bufsize 4000k -c:a aac -b:a 128k`
   into final_chat.mp4 (post the full-quality final.mp4).
7. Check: run qa_video.py on the final (for avatar stretches use `--from/--to`, each starting 0.1 s after a cut; a hard
   cut itself reads as "pixel glitch").

## Design rules
- Captions never cover a face or the source's own burned-in subtitles/logo (check on-screen text positions in the
  analyzer's timeline.md).
- Pill = category or name (NOLLYWOOD GIST, MY TAKE, COMMENT ONE). Title = the hook in 2-4 words. Credit every clip and
  photo ("Clip: <channel> (YouTube)", "Photo: Wikimedia Commons").
- End card: the question as the title, the follow line as the subtitle on follow-line videos.

## Known failures and fixes
- "hyperframes: not found": it is not on PATH; use hf_build.py or `$(npm prefix -g)/bin/hyperframes`.
- Render fails with a Chrome error: `$(npm prefix -g)/bin/hyperframes browser ensure` (or delete
  ~/.cache/hyperframes/chrome and render again).
- GSAP loads from cdn.jsdelivr.net: render needs internet.
- Lint errors are printed by hf_build.py; a missing word file or a word list outside the clip range gives empty
  captions.

## Reinstall
Node 20+, then `bash install.sh` (installs hyperframes globally and Chrome), then `bash selftest.sh`.

## Report
Say which layouts you used, which clips/photos are in it with credits, how long it took, and that HyperFrames used no
credits.
