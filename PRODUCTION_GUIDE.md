# Production guide (first draft)

How an AlterWords agent makes a short vertical video, from topic to posted file. It tells you HOW to make videos.
WHAT to make (your lane, your ideas, your formats) comes from your content file and your own research; WHO you are
(your look, your voice, your tone) comes from your personality identity file. Rules: RULE 0 first
(rules/RULE_0_SOCIAL_ACCESS.md), then rules/STANDING_RULES.md.

Contents
1. Setup
2. Pick your route: free or avatar
3. The pipeline every video follows
4. Free route, step by step
5. Voiceover (agents without a face)
6. Avatar route, step by step (ready for the day you get one)
7. Your look: identity file -> production
8. Checks before posting
9. Posting through Buffer
10. Records for every video
11. Failure playbook
12. Finding and testing new tools on GitHub
13. Export spec

---

## 1. Setup

```
git clone <repo URL> blueprint-kit && cd blueprint-kit
cp settings.example.env settings.env      # fill in your name, handles, colours, fonts, voice, avatar or none
bash install.sh                           # add --with-avatar only if the owner gave you an avatar
```

install.sh sets up FFmpeg, yt-dlp (latest, with the PO-token helper and deno), the free Cloudflare WARP tunnel,
faster-whisper, OpenCV and MediaPipe models, HyperFrames and the Buffer CLI, then runs selftest.sh: a real public
YouTube clip is downloaded, transcribed, edited into a captioned clip card and checked. All passes = you are ready.

Keys never go in the repo. You add your own: your Buffer key in settings.env (or ~/.config/buffer/env), `heygen auth
login` for the avatar route, a text-to-speech key when the owner gives you one. settings.env is in .gitignore.

To update the kit later: `git pull`, then `bash selftest.sh`.

## 2. Pick your route

| | Free route | Avatar route |
|---|---|---|
| Who | Every agent, from day one | Only agents the owner gave a HeyGen avatar |
| Your presence | Your voice (generated voiceover) + your on-screen style | Your face and voice in one HeyGen render |
| Cost per video | 0 (text to speech, when added, costs pennies) | about 0.3 HeyGen credit per second: 9-12 credits for 30-40 s |
| Tools | download, analyze, HyperFrames, FFmpeg | the same + render_avatar.sh and the look checks |

The free route is a complete route, not a lesser one. Clipping, podcast clips, curated deep dives and process videos
all work without a face. When you get an avatar you keep everything and add sections 6 and 7.

## 3. The pipeline every video follows

1. **Topic** - pick from your lane, prove it is moving (standing rule 3), write the signal in notes.txt.
2. **Source** - download the clip(s) you need (download_youtube.sh, download_clip.sh). Public videos only.
3. **Analyze** - analyze_source.py before any cut: words with timestamps, hook/chorus lines, shots, on-screen text, loud
   moments, clean cut ranges.
4. **Script** - hook (keeps its promise), the moment, your take, a two-choice question at the end. 28-40 s spoken.
5. **Voice** - free route: voiceover (section 5) or the clip's own sound; avatar route: one render (section 6).
6. **Edit** - hf_build.py for clip cards, titles and word-by-word captions; FFmpeg to join and mix.
7. **Check** - section 8. A video with a known glitch does not go out.
8. **Review** - the owner reviews, unless the owner allowed the routine to post alone.
9. **Post** - post_everywhere.sh through Buffer only, AI label on.
10. **Record** - notes.txt, posts/index.csv, look log (avatar).

Each video lives in its own folder: `$AGENT_WORK/YYYY-MM-DD_slug/`.

## 4. Free route, step by step

```
W=$AGENT_WORK/2026-11-03_inferno; mkdir -p $W
bash scripts/download_youtube.sh "https://www.youtube.com/watch?v=VIDEO" src $W            # whole video
bash scripts/download_youtube.sh "URL" src $W 00:48-01:05                                 # or one section
python3 scripts/analyze_source.py $W/src.mp4 --lens 4,6,10          # music; add --speech for talk/podcasts
less $W/src_analysis/timeline.md                                    # pick the range from "Cut suggestions"
python3 scripts/hf_build.py --clip $W/src.mp4 --start 48.24 --end 55.24 \
   --words $W/src_analysis/words.json --words-abs --layout card \
   --pill "NEW MUSIC" --title "ARTIST" --subtitle "SONG" --credit "Clip: ARTIST, official video (YouTube)" \
   --out $W/seg1.mp4
```

- **Layouts:** `--layout card` puts the source clip in a rounded card over a blurred copy with a title and captions
  (templates/hyperframes/clip_card). `--layout full` fills the screen with the clip or a talking head, captions in the
  safe band (word_captions, talking_head_captions). A title over a full clip is title_card.
- **Captions:** `AGENT_CAPTION_STYLE=word` lights up each word in your accent colour as it is said; `line` shows plain
  groups. 2-3 words per group for music, 3-5 for talk (`--max-words`). For your own voiceover, take the TEXT from
  your script and the TIMING from Whisper: `--script-file script.txt`.
- **Joining segments:** encode every segment the same way (hf_build does: H.264, 1080x1920, 30 fps, AAC 44.1 kHz),
  then `ffmpeg -f concat -safe 0 -i list.txt -c copy final.mp4`.
- **Picture-in-picture:** scripts/build_video.sh (avatar + clip) and the FFmpeg overlay skill (skills/) show the
  overlay recipes.
- **Charts and cards:** make_chart_example.py (animated bars piped to FFmpeg) and make_banner.py (headline PNG).
- **Render time:** HyperFrames takes about 50 s per 7 s of video on a small cloud machine. Plan for it.

## 5. Voiceover (agents without a face)

Agents without a face speak through a generated voiceover. A real-sounding voice is what makes a faceless video feel
like someone, so the rules are strict.

- **One voice, always.** Pick ONE voice in your identity file and set AGENT_TTS_PROVIDER, AGENT_TTS_VOICE,
  AGENT_TTS_SPEED and AGENT_TTS_STYLE in settings.env. Never switch voices between videos; your audience learns it.
- **Providers:** MiniMax text to speech or Google Gemini text to speech. The owner gives you the key when it is time;
  until then AGENT_TTS_PROVIDER=none and you make clip-led videos where the source's own sound carries the story.
  No API call is written into this kit yet on purpose.
- **Write for the ear.** Short sentences. Numbers written the way they are said ("six thousand naira"). Local phrases
  from your identity file spelled the way they sound. Read it aloud in your head: if you would stumble, rewrite it.
- **Pace:** about 2.5 words per second. A 35 s video holds about 85 spoken words, less when a clip plays in the middle.
- **File:** export WAV or MP3 at 44.1 kHz, save as `$W/voice.wav`, keep script.txt beside it.
- **Level:** normalize the voice to about -14 LUFS
  (`ffmpeg -i voice.wav -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 44100 voice_norm.wav`), and duck the clip's sound to
  10-15% under the voice (build_video.sh shows the ducking filter).
- **Captions:** run `analyze_source.py voice_norm.wav --speech` (Whisper gives the timing), then
  `hf_build.py ... --words <words.json> --script-file script.txt` so the caption text is exactly your script.
  Whisper stays the transcription tool for every route.
- **Check:** listen to the whole file once. Mispronounced names get respelled in the script and the line is
  regenerated, not the whole voiceover.

## 6. Avatar route, step by step (ready for the day you get one)

HeyGen does ONE thing: render your talking avatar. Everything else stays free. One render per video, no test renders.

1. **Sign in once:** `heygen auth login` (OAuth, bills your plan). The kit's `hg` wrapper never uses a separate API
   wallet. Check credits: `. scripts/env.sh; hg_credits`.
2. **Looks:** make 10-20 looks of yourself (outfit, place, framing), all selfie/vlog style, eyes into the lens.
   `scripts/make_looks.sh` generates them from your main close-up (1 credit each, measured). Every new look must pass:
   - face_check.py: same person as your reference (similarity >= 0.50 is what the reference agent required)
   - hand_check.py: no extra fingers, no second right hand, hands whole; check a full frame AND a close-up crop
   - object_check.py and pose_check.py: no warped phones, no stiff posed portrait
   - analyze_start_picture.py: eyes on the lens, head straight, mouth slightly open
   accept_looks.py adds the ones that pass to looks/catalog.json. Keep a gaze audit of your looks.
3. **Pick the look:** `python3 scripts/pick_look.py --topic "what the video is about"` rotates outfits and places and
   avoids recent ones. make_topic_look.sh makes a one-off look for a special topic.
4. **Check the starting picture:** `python3 scripts/analyze_start_picture.py looks/previews/LOOK.jpg --prompt-out
   $W/motion_prompt.txt`. It measures gaze, head angle, hands and objects, and drafts the motion prompt.
5. **Motion prompt:** gaze first, ONE action, short. HeyGen's custom motion only covers about 10 seconds, then loops,
   so a busy prompt repeats a bad gesture. Safest: "Eyes on the lens. Hands still, gentle nods."
   rules/PROMPT_TEMPLATE.md has the full checklist.
6. **Render once:** `bash scripts/render_avatar.sh $W "TITLE" LOOK_ID` (script.txt is spoken inside the render by
   AGENT_VOICE_ID). It refuses to run below AGENT_MIN_CREDITS and logs the credit cost.
7. **QA the raw render:** `python3 scripts/qa_video.py $W/avatar_raw.mp4 --sheet $W/qa.jpg`.
   - Eyes off the lens: **more than 40% of full-screen time = FAIL**, 20-40% = warning.
   - Hands: a shape change, a sixth finger or a third hand is a defect at that time stamp.
   - Face: a sudden size jump or jumping landmarks = morph.
8. **Cut around failures:** never render again to fix a few bad seconds. Put a card, a photo, the source clip or a
   tighter zoom on your face over those time stamps, and only show yourself full screen where you look into the lens.
   Then QA the final video only over your full-screen parts (`--from/--to`).
9. **Credit maths:** about 0.3 credit per rendered second (a 36 s render cost 11 credits). Budget = videos per month x
   about 11 + new looks x 1. Two videos a day for 30 days is about 660 credits, so most agents post avatar videos on
   some slots and free-route videos on the rest. Keep AGENT_MIN_CREDITS in reserve for one render.

## 7. Your look: identity file -> production

Your personality identity file says WHAT your look is (Visual Identity section): your colours, fonts, caption style,
your face and outfits if you have an avatar, your voice. This guide says HOW to apply it:

- Colours -> AGENT_ACCENT, AGENT_INK, AGENT_BG (pill, active caption word, card background).
- Fonts -> AGENT_FONT_DISPLAY (titles), AGENT_FONT_BODY (captions). Google Font names.
- Caption style -> AGENT_CAPTION_STYLE (word or line) and AGENT_CAPTION_POSITION (lower or middle).
- Voice -> AGENT_TTS_* (free route) or AGENT_VOICE_ID (avatar).
- Face and outfits -> AGENT_AVATAR_ID, AGENT_REF_LOOK_ID, AGENT_REF_IMAGE, and your looks catalog.

When your identity file changes your look, change settings.env the same day so every video after it matches.

## 8. Checks before posting

Run on the FINAL file, every time:

- `bash scripts/verify_video.sh final.mp4 HOOK_SEC PAUSE_SEC` (HOOK_SEC and PAUSE_SEC are where the loudness
  segments split; or do the checks below by hand):
  H.264, 1080x1920, AAC audio, clean decode (`ffmpeg -v error -i final.mp4 -f null -` prints nothing), size under
  10 MB if it goes through chat.
- Look at frames: the first frame (it is the thumbnail), every card, every caption. Text must not cover a mouth or a
  credit. Captions match the words.
- Avatar: qa_video.py over your full-screen parts; hands checked frame by frame.
- Facts: every number and quote traced to a source in notes.txt.
- Credit on screen for every clip.

## 9. Posting through Buffer

Only after the owner's yes (or a routine the owner allowed):

```
P=$AGENT_POSTS/2026-11-03_inferno     # holds final.mp4, caption.txt (TikTok), caption_instagram.txt, caption_x.txt
bash scripts/post_everywhere.sh $P --dry-run      # shows what would go out
bash scripts/post_everywhere.sh $P                # TikTok, then Instagram (Reel), then X
```

It posts with the AI label on ("(AI persona)" goes in the X caption), at most 5 hashtags, one hosted link reused for
all three, and writes the post records plus a line in posts/index.csv. For one platform, a schedule or a Buffer draft
the owner can look at first: `bash scripts/buffer_post.sh $P/final.mp4 $P/caption.txt $P --platform tiktok --mode draft`
(or `--due 2026-11-03T17:00:00+01:00`). If Buffer shows "sending" for a long time, do NOT post again: wait and
read the post again.

## 10. Records for every video

`$AGENT_WORK/<date_slug>/notes.txt`:
```
topic, category, why now (the signal + links), sources (every clip and fact with its link)
script (as spoken), hook, ending question, follow line yes/no, tests this video is part of
route (free/avatar), look code, voice, render id, credits before/after
checks: eyes-down %, hand defects and how they were covered, final file checks
posted: times and links per platform
```
buffer_post.sh adds the post to posts/index.csv. `bash scripts/log_performance.sh` (read-only) pulls Buffer's numbers
for every post into performance_log.csv. Avatar: log the look with pick_look.py --log.
The engagement review (rules/ENGAGEMENT_RULES.md) reads these.

## 11. Failure playbook

| Problem | What to do |
|---|---|
| YouTube: "Sign in to confirm you're not a bot" | `bash scripts/warp_up.sh --restart`, then retry; download_youtube.sh already reconnects up to 15 times |
| YouTube: PO token errors | check the PO-token server: `curl -s localhost:4416/ping`; `bash scripts/warp_up.sh` starts it |
| yt-dlp suddenly fails on every site | `python3 -m pip install --user -U --pre "yt-dlp[default]" yt-dlp-ejs` |
| TikTok download gives HEVC | download_clip.sh prefers H.264; if not available re-encode with libx264 |
| Whisper crashes with "metadata_errors" | use the kit's scripts (they pass decoded audio); do not call faster-whisper on the file directly |
| Whisper gets lyrics wrong | fix words with `hf_build.py --replace` from official/on-screen lyrics |
| HyperFrames lint error | read the message; most are a missing asset; rerun with `--no-render` and open index.html |
| File over 10 MB | build_video.sh raises CRF automatically; for HyperFrames output re-encode with a higher CRF |
| Buffer "sending" for a long time | wait, read again; never repost |
| Buffer returns an old handle in the link | set AGENT_BUFFER_TIKTOK_OLD_HANDLE / AGENT_X_ACCOUNT_NUMBER |
| Avatar: eyes down > 40% | cut around it; if the whole render fails, report to the owner before a second render |
| Avatar: hand glitch | cover with a card or zoom; never post it |
| Credits below AGENT_MIN_CREDITS | free-route video for this slot; tell the owner |
| Machine reset, tools missing | `bash install.sh` then `bash selftest.sh` |

## 12. Finding and testing new tools on GitHub

- Search GitHub for the job, not the brand ("word level captions ffmpeg", "tiktok downloader"). Prefer projects with
  a release in the last 6 months, an open-source licence, and issues that get answers.
- Read the README and the licence before installing. Never run an install script that asks for your keys or a login
  to a social account (RULE 0).
- Test in a scratch folder on the selftest clip first, compare with what the kit already does (speed, quality, cost),
  and write the result in your playbook.
- If it is better, add it as a new script with its own doc in skills/, pin its version in install.sh, and run
  selftest.sh. Share it with the owner so the whole kit gets it.

## 13. Export spec

- Container MP4, video H.264 (High), yuv420p, 1080x1920, 25-30 fps constant, `-movflags +faststart`.
- Audio AAC, 44.1 kHz, stereo, 128-160 kb/s; voice around -14 LUFS, true peak under -1 dB.
- Length 28-40 s (the hook in the first 2 s); keep busy-background videos nearer 35-40 s.
- Size under 10 MB when sent through chat (CRF 23-30), otherwise CRF 18-23.
- Safe zones: keep text out of the top 150 px and bottom 380 px (platform buttons and captions sit there).
- Captions burned in. AI label on every platform. Clip credit on screen.
