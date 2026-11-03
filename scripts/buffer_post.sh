#!/usr/bin/env bash
# Post a finished video to ONE Buffer channel (TikTok, Instagram Reel or X), AI label ON.
# Only run after the owner said yes to this exact video.
# Usage: buffer_post.sh VIDEO.mp4 CAPTION.txt POSTDIR [--platform tiktok|instagram|x] [--mode shareNow|addToQueue|shareNext|draft]
#                      [--due 2026-10-17T16:30:00+01:00] [--url HOSTED_URL] [--dry-run]
#   --platform defaults to tiktok. --due switches to customScheduled. --url reuses an existing public link (no new upload).
#   Writes POSTDIR/{asset,payload,create_result,post_status}[_instagram|_x].json and a line in posts/index.csv.
#   Usually called by post_everywhere.sh, which runs all three channels in order.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
V=${1:?video}; CAP=${2:?caption file}; D=${3:?post dir}; shift 3
PLAT=tiktok; MODE=shareNow; URL=""; DRY=0; DUE=""
while [ $# -gt 0 ]; do case "$1" in
  --platform) PLAT=$2; shift 2;; --mode) MODE=$2; shift 2;; --url) URL=$2; shift 2;; --due) DUE=$2; shift 2;;
  --dry-run) DRY=1; shift;; *) echo "unknown arg $1" >&2; exit 2;; esac; done
mkdir -p "$D"
[ -n "${BUFFER_API_KEY:-}" ] || { echo "BUFFER_API_KEY not loaded" >&2; exit 2; }

# per-platform channel, caption limits, file suffix
case "$PLAT" in
  tiktok)    CH=$AGENT_BUFFER_CHANNEL; MAXC=2200; MAXT=5; SFX="";;
  instagram) CH=$AGENT_BUFFER_IG;      MAXC=2200; MAXT=5; SFX="_instagram";;
  x|twitter) PLAT=x; CH=$AGENT_BUFFER_X; MAXC=280; MAXT=2; SFX="_x";;
  *) echo "platform must be tiktok, instagram or x" >&2; exit 2;;
esac
CHARS=$(printf '%s' "$(cat "$CAP")" | wc -m); TAGS=$(grep -o '#[A-Za-z0-9_]*' "$CAP" | wc -l)
[ "$CHARS" -le "$MAXC" ] || { echo "$PLAT caption too long ($CHARS > $MAXC)" >&2; exit 2; }
[ "$TAGS" -le "$MAXT" ] || { echo "$PLAT: too many hashtags ($TAGS, max $MAXT)" >&2; exit 2; }
echo "$PLAT caption: $CHARS chars, $TAGS hashtags"

# 1. channel must be connected and unlocked
ch=$(buffer channels get --id "$CH" --fields id,name,service,isDisconnected,isLocked,isQueuePaused --output json)
echo "channel: $ch"
echo "$ch" | jq -e '.isDisconnected==false and .isLocked==false' >/dev/null || { echo "STOP: $PLAT channel disconnected or locked; owner must reconnect it in Buffer" >&2; exit 3; }

# 2. public link (HeyGen asset upload, free). Reuse the TikTok upload when it exists: same file, same link.
if [ -z "$URL" ] && [ -f "$D/asset.json" ]; then
  U0=$(jq -r '.data.url // empty' "$D/asset.json"); S0=$(jq -r '.data.size_bytes // 0' "$D/asset.json")
  [ -n "$U0" ] && [ "$S0" = "$(stat -c %s "$V")" ] && URL=$U0 && echo "reusing hosted link from asset.json"
fi
if [ -z "$URL" ]; then
  if [ $DRY -eq 1 ]; then URL="https://resource2.heygen.ai/video/DRYRUN/original.mp4"; echo "[dry-run] would upload $V to HeyGen assets"
  else
    hg asset create --file "$V" > "$D/asset$SFX.json" 2> "$D/asset_err$SFX.txt"
    URL=$(jq -r '.data.url // empty' "$D/asset$SFX.json")
    [ -n "$URL" ] || { echo "upload failed (see asset_err$SFX.txt)" >&2; exit 1; }
  fi
fi
if [ $DRY -eq 0 ]; then
  curl -sI "$URL" | grep -iE '^(HTTP|content-type)' | tee "$D/url_check$SFX.txt"
  grep -qi 'content-type: video/' "$D/url_check$SFX.txt" || { echo "hosted URL is not serving video" >&2; exit 1; }
fi

# 3. payload: one video, AI-generated disclosure always true
EXTRA='{}'
case "$MODE" in
  shareNow|addToQueue|shareNext) ;;
  draft) MODE=addToQueue; EXTRA='{"saveToDraft":true}';;
  *) echo "mode must be shareNow, addToQueue, shareNext or draft" >&2; exit 2;;
esac
if [ -n "$DUE" ]; then MODE=customScheduled; EXTRA=$(jq -nc --arg d "$DUE" '{dueAt:$d}'); fi
case "$PLAT" in
  tiktok)    META='{"tiktok":{"isAiGenerated":true}}'; VMETA='{"thumbnailOffset":1000}';;
  instagram) META='{"instagram":{"type":"reel","shouldShareToFeed":true,"isAiGenerated":true}}'; VMETA='{"thumbnailOffset":1000}';;
  x)         META='{"twitter":{"isAiGenerated":true}}'; VMETA='{}';;   # thumbnailOffset is not supported on X
esac
P="$D/payload$SFX.json"
jq -nc --arg ch "$CH" --rawfile t "$CAP" --arg u "$URL" --arg m "$MODE" --argjson x "$EXTRA" --argjson meta "$META" --argjson vm "$VMETA" \
  '{channelId:$ch, schedulingType:"automatic", mode:$m, text:($t|rtrimstr("\n")), assets:[{video:({url:$u} + (if $vm=={} then {} else {metadata:$vm} end))}], metadata:$meta} + $x' > "$P"
buffer posts create --input "$P" --dry-run > /dev/null
echo "payload valid (local dry-run):"; jq -c '{mode, dueAt, url: .assets[0].video.url, metadata}' "$P"
[ $DRY -eq 1 ] && { echo "[dry-run] nothing sent"; exit 0; }

# 4. create (NOT idempotent: if unclear, check buffer posts list before any retry)
buffer posts create --input "$P" --output json > "$D/create_result$SFX.json"
cat "$D/create_result$SFX.json"; echo
jq -e '.__typename=="PostActionSuccess"' "$D/create_result$SFX.json" >/dev/null || { echo "Buffer did not accept the $PLAT post" >&2; exit 1; }
PID=$(jq -r .post.id "$D/create_result$SFX.json")

# 5. poll until sent or error (shareNow usually takes 1 to 3 minutes); scheduled posts stop at 'scheduled'
for i in $(seq 1 24); do
  buffer posts get --id "$PID" --fields id,status,sentAt,dueAt,externalLink,error.message --output json > "$D/post_status$SFX.json"
  st=$(jq -r .status "$D/post_status$SFX.json"); echo "status: $st"
  case "$st" in sent|error|draft|scheduled|buffer) break;; esac
  sleep 20
done
cat "$D/post_status$SFX.json"; echo
# Buffer links sometimes show an old TikTok handle, or a numeric X account number instead of the handle: fixed from settings.env
LINK=$(jq -r '.externalLink // empty' "$D/post_status$SFX.json" | sed -e "${AGENT_BUFFER_TIKTOK_OLD_HANDLE:+s#@$AGENT_BUFFER_TIKTOK_OLD_HANDLE#@$AGENT_TIKTOK_HANDLE#}" -e "${AGENT_X_ACCOUNT_NUMBER:+s#x.com/$AGENT_X_ACCOUNT_NUMBER/#x.com/$AGENT_X_HANDLE/#}")
echo "$(date -u +%F),$PID,$(basename "$D"),$LINK,$PLAT" >> "$AGENT_POSTS/index.csv"
echo "$PLAT POST $PID  LINK: ${LINK:-none yet (scheduled or still sending: fill it in later with buffer posts get)}"
