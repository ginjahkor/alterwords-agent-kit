# Skill: Post to socials with Buffer

## RULE 0, ABOVE EVERYTHING IN THIS SKILL: BUFFER API ONLY
Never use a web browser or web login on your TikTok, Instagram or X (no browser automation, no saved logins, no
verification codes). Never check your own posts or profile outside Buffer: no opening your post links, no yt-dlp on your
handles, no curl/fetch of your public pages, no X readers or search on your own posts, no scraping. Post, check status
and read engagement through the Buffer API only. When Buffer can't do something (comment text, replies, profile edits,
deleting a published post, region visibility, sounds), say so plainly in the report and stop: no fallback. Full text:
rules/RULE_0_SOCIAL_ACCESS.md.

Every video goes to TikTok, Instagram (Reel) and X by default, each with its own caption.
Scripts: `scripts/post_everywhere.sh` (all three) and `scripts/buffer_post.sh` (one platform).

## Setup (once, per agent)
- `. scripts/env.sh` adds the Buffer CLI to PATH and loads settings.env (BUFFER_API_KEY, AGENT_BUFFER_ORG,
  AGENT_BUFFER_CHANNEL (TikTok), AGENT_BUFFER_IG, AGENT_BUFFER_X, your handles).
- Buffer CLI `@bufferapp/cli` (install.sh). Never print, echo, cat, log or read the key aloud; check only with
  `[ -n "$BUFFER_API_KEY" ]`. Never run `buffer init`.
- Find your organization and channel IDs with `buffer channels list --output json` and put them in settings.env
  (never in the repo).
- Re-verify any channel with
  `buffer channels get --id ID --fields id,name,service,type,isDisconnected,isLocked,isQueuePaused --output json`;
  if disconnected or locked, STOP and tell your owner to reconnect it in the Buffer app.

## What Buffer can do per platform (verified by the reference agent)
- TikTok: 1 video, 3 s to 10 min, up to 1 GB, cover via assets[].video.metadata.thumbnailOffset (ms). shareNow goes
  "sending" to "sent" in about 2 minutes. metadata.tiktok.isAiGenerated true shows "Creator labeled as AI-generated".
  Photo posts (2 to 10 JPGs) can't carry music or the AI label. No TikTok sounds, Stories, stickers or polls via API;
  caption max 2,200 chars, MAX 5 hashtags. Buffer's TikTok link may still use an old handle after a rename: set
  AGENT_BUFFER_TIKTOK_OLD_HANDLE and buffer_post.sh swaps it.
- Instagram: metadata.instagram.type reel | post | story; shouldShareToFeed true for reels; isAiGenerated true shows "AI
  content" under the username. Reels 3 s to 15 min, 9:16, 23 to 60 fps; caption max 2,200 chars; max 5 hashtags.
  shareNow took about 3 minutes to reach "sent". Returns an instagram.com/reel/... link. thumbnailOffset works. No
  music from Instagram's library via the API. Instagram turns any @name in the caption into a link to that Instagram
  account, even when the text says "on TikTok".
- X: metadata.twitter.isAiGenerated exists but X shows no visible label, so every X caption ends with "(AI persona)".
  X Free: 280 characters, 1 video 0.5 to 140 s, up to 1080x1920 and 512 MB, MP4 H.264/AAC. Don't send
  thumbnailOffset. shareNow is "sent" within seconds. Buffer's link may use the numeric account number instead of the
  handle: set AGENT_X_ACCOUNT_NUMBER and buffer_post.sh swaps in the handle.
- A standard video (1080x1920 H.264/AAC, 30 to 45 s, under 10 MB) fits all three with no re-encode.
- Metrics: `buffer posts get --id ID --fields metrics.type,metrics.value,metricsUpdatedAt`. scripts/log_performance.sh
  logs every post in $AGENT_POSTS/index.csv. Metrics refresh about once a day. Metrics include comment COUNTS, never
  comment text: Buffer's public API can't read or reply to comments.

## Hosting
Media must be a public, direct, stable HTTPS URL. The free method the reference agent used: upload to your HeyGen
assets with `hg asset create --file VIDEO.mp4` and use data.url (costs no credits). buffer_post.sh uploads once and
reuses POSTDIR/asset.json's link for the other platforms when the file size matches. Verify with `curl -sI URL` (your
file host, not a social site, so it's allowed). No Google Drive/Dropbox share links. No other host without your
owner's OK. Agents without HeyGen: ask your owner which host to use.

## Rules
0. RULE 0 wins over every rule here.
1. Read-only Buffer commands run freely.
2. Every write (posts create incl. drafts, edit, delete, ideas) needs your owner's go-ahead for that exact video and
   captions, unless a schedule or skill your owner set up already covers it. shareNow publishes instantly with no
   approval inside Buffer, so never say your owner will approve "in Buffer" unless you used --mode draft.
3. Always validate locally (`--dry-run`), then send with `--output json`; only `__typename` PostActionSuccess is
   success. `posts create` is NOT idempotent: if unclear, check
   `buffer posts list --organization-id "$AGENT_BUFFER_ORG"` before any retry.
4. Modes: shareNow, addToQueue, shareNext, customScheduled (dueAt with offset, e.g. 2026-10-20T18:00:00+01:00;
   buffer_post.sh --due), saveToDraft true for a draft.
5. AI disclosure on every post, every platform: TikTok and Instagram through isAiGenerated, X through "(AI persona)" in
   the caption plus isAiGenerated.
6. Limits (free plan): 10 scheduled posts at a time, TikTok 25 posts a day, API key 100 requests per 15 min and 250 a
   day.
7. Spacing: the same video can go to all three platforms at once. Two different videos on one platform the same day: at
   least 30 minutes apart (use --due).
8. Deleting a post in Buffer only removes it from Buffer, not from the platform. Take-downs of published posts: your
   owner does them in the app; you tell them which post and why. Never in a browser.

## Captions, one per platform, in your own voice (your identity file)
- POSTDIR/caption.txt, TikTok: headline in capitals, a line of your take, the closing question, the subject's handle,
  max 5 hashtags including your own tag.
- POSTDIR/caption_instagram.txt, Instagram Reel: headline on its own line, two or three short sentences, the question,
  the subject's Instagram handle, max 5 hashtags. Credit a clip from another platform by name without the @ ("Clip:
  creatorname on TikTok") unless you've confirmed the Instagram account with that name is the same creator.
- POSTDIR/caption_x.txt, X: one or two sentences, the question, the subject's X handle, 1 or 2 hashtags max, ending
  "(AI persona)". Under 280 chars (aim for 240).
The script refuses captions over the length or hashtag limit for that platform.

## One command
```
. scripts/env.sh
scripts/post_everywhere.sh POSTDIR --dry-run
scripts/post_everywhere.sh POSTDIR                  # TikTok, Instagram, X, shareNow; a failure on one carries on
scripts/post_everywhere.sh POSTDIR --only instagram,x
scripts/buffer_post.sh POSTDIR/final.mp4 POSTDIR/caption_x.txt POSTDIR --platform x --due 2026-10-18T16:10:00+01:00
```
Files per platform in POSTDIR: TikTok asset/payload/create_result/post_status.json; Instagram and X the same names
with _instagram / _x. Each post adds a row (date, post ID, folder, link, platform) to $AGENT_POSTS/index.csv. For a
scheduled post the link is empty until it sends: fill it in from `buffer posts get --id ID --fields status,externalLink`.

## After posting, check every post IN BUFFER ONLY (RULE 0)
1. For each platform: `buffer posts get --id ID --fields id,status,externalLink,dueAt,sentAt --output json`. Status
   `sent` with an externalLink = live. Report that link; do NOT open it, fetch it or check it any other way.
2. Status still "sending" after about 15 minutes: re-read it in Buffer a few times. Never repost. If it stays stuck or
   shows "error", report Buffer's status and error text and stop.
3. The AI label: report that isAiGenerated (and "(AI persona)" on X) was in the payload Buffer accepted. Don't claim
   you saw the label, caption or sound on the platform.
4. Report per platform: mode, local time, Buffer post ID, status, link. Never include the key.
5. Run scripts/log_performance.sh after about 24 and 72 hours.
6. Profiles can't be edited through Buffer, and you never sign in to TikTok, Instagram or X. Report the needed fixes and
   the exact text; your owner makes them.
7. Whether TikTok hides a video in some regions can't be seen through Buffer. Don't guess and don't check public pages.
