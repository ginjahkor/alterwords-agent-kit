# Playbook: lessons from the reference agent

The reference agent posted two videos a day to TikTok, Instagram and X for weeks before this kit was written. These
are the lessons that cost it something to learn, made general. Your own playbook grows from here: add a dated line
every time something goes wrong and how you fixed it.

## How a day runs
- Two slots a day (the reference agent used 6 AM and 5 PM local time). Start the work early enough that the video is
  checked before the slot. If the slot is missed, post when ready and say it was late.
- A daily engagement review at a time that does not clash with posting (the reference agent used 10 AM).
- Every video: pick and prove a topic -> source -> analyze -> script -> (avatar render) -> edit -> check -> owner
  review if required -> post through Buffer -> record.

## Topics and sources
- **Finding TikTok sources without a login:** TikTok search and tag pages show nothing signed out, and yt-dlp's tag
  extractor is broken. What works: list a creator's recent posts with
  `yt-dlp --flat-playlist -I 1:40 --print "%(id)s %(upload_date)s %(view_count)s %(like_count)s %(duration)s %(title).100s" https://www.tiktok.com/@HANDLE`
  on accounts that cover the topic, and compare a video's numbers with that creator's usual numbers.
- **TikTok's trending pages show a puzzle** to cloud machines. Do not try to get past it; say official charts were not
  checked.
- **No clip you may use?** A news or numbers story works with your own visuals: a chart (make_chart_example.py shows
  how), text cards, photos with slow zooms.
- **Reusing your own earlier clip** works for follow-up videos ("remember when...").
- **An explicit owner request beats the topic rules** for that one video; say in the report that it was an exception.

## Audio and clips
- **Quiet clips:** a fan-filmed clip can sit at -27 dB, far under a voice. Normalize first:
  `ffmpeg -i clip.mp4 -c:v copy -af loudnorm=I=-10:TP=-1.0:LRA=11 -ar 44100 -c:a aac -b:a 160k clip_norm.mp4`.
- **Short clips:** when the clip is shorter than the part it fills, loop it:
  `ffmpeg -stream_loop 4 -i clip.mp4 -t 45 -c:v libx264 -crf 18 -c:a aac clip_loop.mp4`.
- **The clip's own sound leads.** A song or a quote playing at full volume for 4-13 seconds in the middle held
  attention better than talking over it. Keep excerpts short.
- **HEVC plays badly on phones:** always fetch or export H.264.
- **Whisper and sung lyrics:** Whisper mishears songs. Fix the words from on-screen or official lyrics.
- **faster-whisper's own decoder can crash** with some PyAV versions ("unexpected keyword argument metadata_errors").
  The kit's scripts pass a decoded audio array instead.

## Edit and file size
- **Busy backgrounds blow up file size.** Keep those videos nearer 35-40 s, or accept a higher CRF.
- **10 MB is the chat limit.** build_video.sh raises CRF until the file fits.
- **Captions must not cover the mouth** or the clip's own credit. Check the first frame and every card.

## Avatar route (when you have one)
- **Same look every time gets noticed.** Make several looks, let pick_look.py choose by topic, and log each use.
- **Eyes on the lens.** A motion prompt that mentions the phone sends the eyes down to the screen. Gaze comes first in
  every prompt (rules/PROMPT_TEMPLATE.md).
- **One action per motion prompt.** HeyGen's custom motion only covers about 10 seconds, then loops or holds, so one
  bad gesture repeats. "Hands still, gentle nods" was the safest.
- **Two right hands:** a starting picture passed an old check that only counted fingertips and then rendered with two
  right hands. hand_check.py now checks handedness and shape on every frame, and the start picture is checked before
  rendering.
- **Hands that stretch or change shape** in the first second are common. Cover them with a card, a photo or a tighter
  zoom on the face instead of rendering again.
- **Credits disappear into extras** (voice files, test renders, new looks). One render per video, voice inside it,
  everything else free.

## Buffer and posting
- **Buffer published without an approval step** once (shareNow is immediate). The owner reviews first; only then
  does buffer_post.sh run. Use `--mode draft` when the owner wants to see it inside Buffer.
- **Buffer's TikTok status can stick on "sending"** after the post is live. Never repost; wait and read it again.
- **Buffer's links** can show an old TikTok handle or the X account's number instead of its handle. Set
  AGENT_BUFFER_TIKTOK_OLD_HANDLE and AGENT_X_ACCOUNT_NUMBER in settings.env and buffer_post.sh fixes the link.
- **Hashtags:** at most 5 per post (Instagram's cap). buffer_post.sh refuses more.
- **AI label per platform:** TikTok and Instagram take Buffer's AI flag; X shows no label, so the X caption carries
  "(AI persona)".
- **Photo posts to TikTok** cannot carry music or the AI label, so post videos.
- **A platform may hide a video** in some places (the reference agent saw this on money and brand stories). Buffer
  cannot show it: ask the owner to check the video's analytics in the app.

## Machines and outages
- **The machine can go down** (502/503 errors). Report it as the blocker, do not pretend work happened, retry later.
  Finished files stay on disk.
- **Never print a token** while checking a sign-in. `hg_credits` in env.sh reads only the credit number.
- **Reinstall after a reset:** `bash install.sh` puts everything back; `bash selftest.sh` proves it.
