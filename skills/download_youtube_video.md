# Skill: Download YouTube video

Download a PUBLIC YouTube video (official music video, interview, trailer, news clip, podcast) as an H.264 MP4. It is
step 1 of most videos ("Make a video" calls it by name). Tested by the reference agent on music videos, a film
announcement and news clips.

## RULE 0 (never break)
- No cookies, no browser logins, no Google/YouTube account, no `--cookies-from-browser`. Public videos only.
- This never touches your own TikTok/Instagram/X accounts. Those are reached only through the Buffer API.
- Never pay for proxies. The route below is free (Cloudflare WARP, anonymous device).

## Why the special route
YouTube blocks most cloud machines ("Sign in to confirm you're not a bot"). The fix is three parts together:
1. Latest yt-dlp (nightly/master) + `yt-dlp-ejs` with deno (solves YouTube's JS challenges).
2. `bgutil-ytdlp-pot-provider` plugin + its local PO-token server on 127.0.0.1:4416 (yt-dlp uses it automatically).
3. Traffic goes out through Cloudflare WARP via `wireproxy` as SOCKS5 on 127.0.0.1:40000. Some WARP exit IPs are
   blocked too (about half, on a bad day), so the script reconnects for a new exit IP up to 15 times. Once that took
   about 5 minutes.

install.sh sets all of this up.

## Files
- `scripts/warp_up.sh`: starts wireproxy + the PO-token server if they're down, prints `ip=` / `warp=on` /
  `pot-server=on`. `--restart` = new exit IP.
- `scripts/download_youtube.sh`: the downloader (calls warp_up.sh itself).
- `$TOOLS_DIR/warp/`: wgcf, wireproxy and this agent's own WARP files (keys inside: never print, send or commit them).
- `$TOOLS_DIR/bgutil-ytdlp-pot-provider/server/`: PO-token server, log `$TOOLS_DIR/bgutil_server.log`.

## Use
1. Find the video (search goes through the tunnel too):
   `bash scripts/warp_up.sh`
   `yt-dlp --proxy socks5h://127.0.0.1:40000 --flat-playlist --print "%(id)s|%(title)s|%(channel)s|%(view_count)s|%(duration)s" "ytsearch8:ARTIST SONG official video"`
   Prefer the OFFICIAL channel (artist/label, film producer, TV station). Note the channel for the on-screen credit.
2. Download:
   `bash scripts/download_youtube.sh "https://www.youtube.com/watch?v=ID" OUT_NAME $AGENT_WORK/OUT_NAME [SECTION]`
   - SECTION is optional, e.g. `00:45-01:20`: it downloads the whole video, then also writes OUT_NAME_cut.mp4 with
     that range. (Do not use yt-dlp --download-sections: ffmpeg can't use the SOCKS tunnel and it hangs.)
   - Run long downloads in the background so a tool timeout can't kill them:
     `(setsid nohup bash scripts/download_youtube.sh URL NAME DIR > DIR/dl.log 2>&1 &)` then poll `tail DIR/dl.log`.
3. Output: DIR/OUT_NAME.mp4 (H.264 up to 1080p + AAC) and DIR/OUT_NAME_meta.txt =
   `title|channel|views|upload_date|duration|url|vcodec|WxH`.
4. Check: the script prints ffprobe (codec, size, duration). Confirm the duration matches YouTube's and the file plays.
   Then hand it to "Analyze and transcribe a source video".

Accepted URL forms: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/, m.youtube.com/watch?v=. Playlists are
refused (--no-playlist).

## Known failures and fixes
- "YouTube blocked this WARP exit (try N), reconnecting...": normal, it retries itself.
- "YouTube download FAILED on every route": wait 10 minutes and run again once. If it still fails, use an official clip
  posted on X/TikTok by the artist or outlet, credit it on screen, and say so in the report. Never use cookies.
- "WARP tunnel not answering": `bash scripts/warp_up.sh --restart`; check `$TOOLS_DIR/warp/wireproxy.log`. If the WARP
  device stopped working, delete wireproxy.conf and rerun install.sh (it registers a new anonymous device).
- `pot-server=off`: `bash scripts/warp_up.sh` starts it; `curl http://127.0.0.1:4416/ping` must answer.
- "Sign in to confirm you're not a bot" even through WARP, or "n challenge solving failed": update yt-dlp + ejs:
  `python3 -m pip install --user -U --pre "yt-dlp[default]" yt-dlp-ejs`. YouTube changes often; yt-dlp nightly is
  usually fixed within days.
- "Download step failed after the check passed": run again (new exit IP).
- Age-restricted or members-only videos can't be downloaded without a login: skip them (RULE 0).
- Max file size 400 MB; for long podcasts use SECTION.

## Reinstall
`bash install.sh` (it skips what is already there), then `bash selftest.sh`. Keep the PO-token server version the
same as the pip plugin version (both pinned in install.sh).

## Report
Say which video (title, channel), that it came from YouTube, and how long it took if retries were needed. If you used
X/TikTok instead, say why and whose clip it is.
