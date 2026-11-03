# Source analysis and edit tools (quick reference)

All rules stay: RULE 0 and the standing rules. Full detail is in PRODUCTION_GUIDE.md and the skills/ folder.

1. **YouTube:** `scripts/download_youtube.sh URL NAME [DIR] [START-END]`. Latest yt-dlp + yt-dlp-ejs (deno) + the
   bgutil PO-token server, through a free Cloudflare WARP tunnel (`scripts/warp_up.sh`), because YouTube blocks most
   cloud IPs. Some WARP exits are blocked too; the script reconnects up to 15 times (allow up to 5 minutes). No cookies,
   no logins.
2. **TikTok:** `scripts/download_clip.sh URL NAME [DIR]` for public videos only. Prefers a single-file H.264 MP4.
3. **Before cutting:** `python3 scripts/analyze_source.py CLIP.mp4 [--speech] [--find "a man kneeling with a ring"]`
   -> CLIP_analysis/timeline.md: word-timed transcript, chorus/hook lines, shots with labels and on-screen text (OCR),
   energy rises, suggested cut ranges that never cut mid-word, cut_*.srt and cut_*_words.json. About 3 minutes for a
   3.5-minute song. Whisper is weak on sung lyrics: fix words from the on-screen or official lyrics (hf_build
   --replace). For your own render or voiceover, captions take the TEXT from script.txt and the TIMING from Whisper
   (hf_build --script-file).
4. **Produced look:** `python3 scripts/hf_build.py` (HyperFrames, free, local): `--layout card` = source clip in a
   rounded card over a blurred copy, title + word-by-word captions; `--layout full` = a full-screen clip or talking
   head with captions in the safe band. About 50 s of render time per 7 s of video. Join segments with FFmpeg.
   Never run `hyperframes auth login` or HyperFrames' HeyGen recipes (that spends credits).
