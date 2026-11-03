# Skill: Make a video

The end-to-end recipe for one short vertical video (trend reaction, trend sound, clip with commentary, or a video about
yourself as an AI), from topic to the three captions. It calls the other skills BY NAME; load each before its step.

Two routes:
- **Voiceover route (default, no face, free):** your generated voice over clip cards, photo cards and captions. See
  PRODUCTION_GUIDE.md, "Voiceover".
- **Avatar route (only if your owner gives you an avatar and credits):** ONE HeyGen render of your talking head per
  video, checked frame by frame, then edited with the same free tools.

## Read first, every time
rules/RULE_0_SOCIAL_ACCESS.md, rules/STANDING_RULES.md, rules/ENGAGEMENT_RULES.md, rules/PROMPT_TEMPLATE.md (avatar
route), your own identity file, rules/PLAYBOOK.md. If anything disagrees: RULE 0 wins, then STANDING_RULES, then
ENGAGEMENT_RULES, then PROMPT_TEMPLATE, then the playbook.

## RULE 0 (short form)
Your own TikTok, Instagram and X are touched ONLY through the Buffer API: posting, post status, metrics, comment
counts. Never a browser or web login on your accounts; never check your own posts outside Buffer. When Buffer can't do
something, say so and stop. Still allowed: research on and downloads of OTHER creators' public posts and public YouTube
videos, news and web research.

## The pipeline (three free skills)
- "Download YouTube video": the source clip from the OFFICIAL upload where one exists. Fallback only if YouTube fails on
  every route: the official or a fan clip from X/TikTok ("Download TikTok video"), cropped to the original footage and
  credited.
- "Analyze and transcribe a source video": pick the moment you cut; and time your own captions (`--speech` on your
  voiceover or render). Song words come from official/on-screen lyrics, your caption words from script.txt.
- "HyperFrames edit": clip cards, photo cards, word-by-word captions, then FFmpeg assembly and loudness.

## Content rules (short form; full text in the rule files)
- Trending people and topics your audience is talking about today, with your own angle. Only checked facts; leave out
  unverified figures. 25 to 40 s, one clear take, one question at the end.
- Hook in the first two seconds: first sentence at most 10 words with the name plus the surprising fact or conflict, and
  something on screen from frame 0 that makes the same promise. Cards start by about 4 s.
- Easy comment question: one word or a pick ("A or B? Comment one."). The end card repeats it; the first caption line
  is the same question.
- Follow line in about half your videos (alternate; write follow_cta yes/no in notes.txt). Never with gifts.
- Real pictures and clips: at least two real visuals when they exist. Sources, best first: official YouTube uploads and
  the person's own posts, Wikimedia Commons, other people's public posts, news photos briefly. Credit every picture and
  clip in words. Never AI-generate or fake a picture of a real person or event.
- Show your life, never announce plans. Never talk about how your videos get made (credits, tools, Buffer). Never
  pretend to be human; never invent comments, events, numbers or experiences.
- Vary categories; never two music videos in a row (check $AGENT_POSTS/index.csv for the last category).
- Trend sounds: download the official upload or the creator's public post, find the hook with the analyzer, keep the
  excerpt short and credit it.

## Procedure (POSTDIR = $AGENT_POSTS/YYYY-MM-DD_slug)
1. **Trend:** prove it with real signals (news outlets, official statements, YouTube upload dates and views, public
   conversation). Save the evidence in POSTDIR/notes.txt, including what you left out as unverified.
2. **Source clip and pictures:** "Download YouTube video" (run it in the background). Real pictures into POSTDIR/media/
   with their sources.
3. **Analyze the source:** analyze_source.py (music default, `--speech` for talk, `--find` for a moment). Read
   timeline.md and the contact sheet; pick the 4-7 s moment on word boundaries; note the source's on-screen text.
4. **Script:** POSTDIR/script.txt; about 2.5 words per second, 25-40 s with the clip. Plan where the source clip plays
   with its own sound (between two of your sentences).
5. **Voice:**
   - Voiceover route: generate script.txt with your ONE fixed voice (AGENT_TTS_PROVIDER / AGENT_TTS_VOICE) into
     POSTDIR/voice.wav. Listen-check by tools: duration, no clipping, loudness.
   - Avatar route: the voice is spoken inside the render (step 6).
6. **Avatar route only: start picture, analysis, prompt, ONE render.**
   - `eval "$(python3 scripts/pick_look.py --env --topic "TOPIC WORDS")"` sets LOOK_CODE, LOOK_ID, BANNER_Y,
     LOOK_STYLE, PHONE_SIDE.
   - `python3 scripts/hand_check.py PREVIEW.jpg --expect 1` and
     `python3 scripts/analyze_start_picture.py PREVIEW.jpg --look $LOOK_CODE --json POSTDIR/picture_analysis.json --prompt-out POSTDIR/motion_prompt.txt`.
     Eyes must read INTO THE LENS, head within 15 degrees; otherwise remake the picture or pick another look.
   - Edit motion_prompt.txt so every clause matches the picture (gaze first, one free-hand gesture, under 45 words).
   - `scripts/render_avatar.sh POSTDIR "TITLE" "$LOOK_ID" --dry-run`, then without (background). ONE render. Check
     credits first; render_avatar.sh refuses below AGENT_MIN_CREDITS.
   - Check the raw render: `python3 scripts/qa_video.py POSTDIR/raw.mp4 --sheet POSTDIR/qa_raw_sheet.jpg --json POSTDIR/qa_raw.json`.
     List every flagged time (hands, eyes, first second).
7. **Caption timing:** analyze_source.py on voice.wav (or raw.mp4) with `--speech`; fix names against script.txt into
   POSTDIR/an/words_fixed.json; cut per-segment word files.
8. **Edit:** "HyperFrames edit". Voiceover route: a hook card from 0.0 s, fact cards (photos, muted clips) under your
   voice, the source clip with its own sound as an inserted segment, the end card (question as title, follow line as
   subtitle). Avatar route: the same cards over every flagged stretch, you full screen only where the raw check was
   clean, your face window on card stretches. Match levels, concat, loudnorm I=-14. 1080x1920 H.264/AAC, under 40 s.
9. **Check the finished file:** `python3 scripts/qa_video.py POSTDIR/final.mp4 [--from A --to B ...] --sheet POSTDIR/qa_final_sheet.jpg --json POSTDIR/qa_final.json`
   plus stills of every warning, OCR of titles and cards, ffprobe. ANY real defect = do not post: fix it (cover with a
   card, move text, cut) and check again. Avatar route: re-render at most once, only for a defect editing can't fix
   (`RERENDER_REASON="..."`). Write the result in POSTDIR/qa_report.md. You can't watch video: say you checked with
   tools.
10. **Captions:** POSTDIR/caption.txt (TikTok), caption_instagram.txt, caption_x.txt (under 280 characters, ending
    "(AI persona)"). First line = the comment question; credits in words; hashtags within each platform's limit. Then
    `bash scripts/post_everywhere.sh POSTDIR --dry-run`.
11. **Deliver to your owner** as soon as it passes: the video (a chat copy under 10 MB if needed) and a short text: the
    story, your take and question, which clip and moment you used and from where, what the checks found and fixed,
    follow line yes/no, trend sound yes/no, credits used and left (avatar route). Do not post unless your owner already
    said to (or a schedule they set up covers it).
12. **After the yes:** "Post to socials with Buffer". Confirm in Buffer only; report the three links from Buffer without
    opening them. Log the look (avatar route: `python3 scripts/pick_look.py --log POSTDIR $LOOK_CODE`), add the
    experiments row to your playbook, fold new lessons into your rule files and skills. Never repost a `sent` post.
13. **Take-downs:** Buffer cannot delete a published post; your owner deletes it in the app; you say which post and why.

## Write everything down
Every post folder: notes.txt (topic evidence, prompts, Pidgin or slang used, follow_cta yes/no, trend sound yes/no,
anything unverified you left out), media/ with sources, the analysis folders, hf/ segments, the check sheets. Long runs
(downloads, analysis, renders, posting) start in the background with setsid nohup and you poll the log.
