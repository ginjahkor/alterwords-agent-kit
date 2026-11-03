#!/usr/bin/env bash
# Download a PUBLIC YouTube video (official music video, interview, news clip) as H.264 MP4.
# Route: latest yt-dlp + yt-dlp-ejs (deno solves YouTube's JS) + bgutil PO tokens, sent out through the
# free Cloudflare WARP tunnel because YouTube blocks this VM's own IP. Some WARP exits are blocked too
# (about 1 in 2 on 2026-10-30), so it reconnects up to 15 times until YouTube answers. No cookies or logins (RULE 0).
# Usage: download_youtube.sh URL OUT_NAME [DIR] [SECTION]
#   SECTION optional, e.g. "00:45-01:20": downloads the whole video, then also writes DIR/OUT_NAME_cut.mp4
#   with only that range. (yt-dlp --download-sections hangs here: ffmpeg cannot use the SOCKS tunnel.)
# Writes DIR/OUT_NAME.mp4 and DIR/OUT_NAME_meta.txt (title|channel|views|upload_date|duration|url|vcodec|WxH)
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
URL=${1:?url}; OUT=${2:?out name}; DIR=${3:-$AGENT_WORK}; SECTION=${4:-}
case "$URL" in
  https://www.youtube.com/watch?v=*|https://youtube.com/watch?v=*|https://youtu.be/*|https://www.youtube.com/shorts/*|https://m.youtube.com/watch?v=*) ;;
  *) echo "Not a YouTube video URL: $URL" >&2; exit 2;;
esac
mkdir -p "$DIR"
YTDLP=$(command -v yt-dlp)
S=$AGENT_SCRIPTS
P=(--proxy socks5://127.0.0.1:40000)
bash "$S/warp_up.sh" >/dev/null 2>&1
OK=0
for i in $(seq 1 15); do
  if timeout 60 "$YTDLP" "${P[@]}" --no-playlist --skip-download --print id -- "$URL" >/dev/null 2>&1; then OK=1; break; fi
  echo "YouTube blocked this WARP exit (try $i), reconnecting..." >&2
  bash "$S/warp_up.sh" --restart >/dev/null 2>&1
done
if [ $OK = 0 ]; then
  echo "Trying without the tunnel..." >&2
  timeout 60 "$YTDLP" --no-playlist --skip-download --print id -- "$URL" >/dev/null 2>&1 && { OK=1; P=(); }
fi
[ $OK = 1 ] || { echo "YouTube download FAILED on every route. Fall back to an official clip on X/TikTok and credit it. Do NOT use cookies or logins." >&2; exit 1; }
rm -f "$DIR/$OUT.mp4"
timeout 500 "$YTDLP" "${P[@]}" --no-playlist --socket-timeout 30 --retries 3 --max-filesize 400M --force-overwrites \
  -S "vcodec:h264,res:1080,acodec:m4a" --merge-output-format mp4 \
  --print-to-file '%(title)s|%(channel)s|%(view_count)s|%(upload_date)s|%(duration)s|%(webpage_url)s|%(vcodec)s|%(width)sx%(height)s' "$DIR/${OUT}_meta.txt" \
  -o "$DIR/${OUT}.%(ext)s" -- "$URL" 2>&1 | grep -v -E '% of|^WARNING' | tail -3
[ -s "$DIR/$OUT.mp4" ] || { echo "Download step failed after the check passed. Run again (new exit IP)." >&2; exit 1; }
ls -l "$DIR/$OUT.mp4"; cat "$DIR/${OUT}_meta.txt"
ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of compact "$DIR/$OUT.mp4"
if [ -n "$SECTION" ]; then
  A=${SECTION%-*}; E=${SECTION#*-}
  ffmpeg -y -v error -ss "$A" -to "$E" -i "$DIR/$OUT.mp4" -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k "$DIR/${OUT}_cut.mp4"
  ls -l "$DIR/${OUT}_cut.mp4"
fi
