#!/usr/bin/env bash
# Download a public TikTok clip as a single-file H.264 MP4 plus a meta line.
# Usage: download_clip.sh 'https://www.tiktok.com/@user/video/ID' OUT_NAME [DIR]
# Writes DIR/OUT_NAME.mp4 and DIR/OUT_NAME_meta.txt
# (uploader|views|likes|comments|duration|upload_date|url|format|vcodec|acodec|WxH)
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
URL=${1:?url}; OUT=${2:?out name}; DIR=${3:-$AGENT_WORK}
case "$URL" in
  https://www.tiktok.com/@*/video/*|https://vm.tiktok.com/*|https://vt.tiktok.com/*) ;;
  *) echo "Not a public TikTok video URL: $URL" >&2; exit 2;;
esac
mkdir -p "$DIR"
yt-dlp --no-playlist --socket-timeout 30 --retries 2 --max-filesize 200M --force-overwrites \
  -f 'b[vcodec^=h264][format_id!=download][ext=mp4]/b[vcodec^=avc][ext=mp4]/b[ext=mp4]/b' \
  --print-to-file '%(uploader)s|%(view_count)s|%(like_count)s|%(comment_count)s|%(duration)s|%(upload_date)s|%(webpage_url)s|%(format_id)s|%(vcodec)s|%(acodec)s|%(width)sx%(height)s' "$DIR/${OUT}_meta.txt" \
  -o "$DIR/${OUT}.%(ext)s" -- "$URL"
ls -l "$DIR/$OUT.mp4"
cat "$DIR/${OUT}_meta.txt"
ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of compact "$DIR/$OUT.mp4"
