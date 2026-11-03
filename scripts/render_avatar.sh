#!/usr/bin/env bash
# AVATAR ROUTE ONLY. Render ONE HeyGen Avatar IV clip of the agent. Rendering the talking avatar is the ONLY thing
# HeyGen is used for (everything else is free: FFmpeg, HyperFrames).
# Usage: render_avatar.sh WORKDIR "TITLE" LOOK_ID [--dry-run]
# Default: script mode. WORKDIR/script.txt is spoken by the agent's HeyGen voice (AGENT_VOICE_ID) INSIDE the one render
#   (no separate HeyGen voice file, no extra credits). Optional WORKDIR/motion_prompt.txt replaces the default motion prompt.
# Legacy: if WORKDIR/voice_asset.json exists (an audio file I uploaded, e.g. made with a FREE tool), it lip-syncs to that instead.
# Writes request.json, render.json, avatar_raw.mp4, credits.txt. Cost measured on the reference agent: about 0.3 credit per second (11 credits for a 36.4 s render).
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
W=${1:?workdir}; TITLE=${2:?title}; AV=${3:-}; DRY=${4:-}
[ "$AV" = "--dry-run" ] && { DRY=--dry-run; AV=; }
[ -n "$AV" ] || { echo "pass the LOOK_ID from pick_look.py (the default close-up is the old 'same clothes' look)" >&2; exit 2; }
[ "${AGENT_AVATAR_ID:-none}" != none ] || [ -n "$AV" ] || { echo "no avatar: this agent uses the free route" >&2; exit 2; }
VOICE=${AGENT_VOICE_ID:?set AGENT_VOICE_ID in settings.env (your HeyGen voice id)}
# Lesson from the reference agent: selfie/vlog looks feel the most natural. HeyGen docs: a motion prompt controls face, body and gestures only (no camera
# moves), works best as one idea in under two short clauses; expressiveness high|medium|low (API default low).
# So: short prompt = handheld body sway + free-hand gestures + expressive face; the handheld camera feel comes from the
# selfie still itself plus build_video.sh's gentle HANDHELD drift. Old portrait looks keep EXPRESSIVENESS=medium.
# Lesson: an old default said "Talking to her phone at arm's length" - that sent the eyes DOWN to the phone screen
# Gaze always comes first now, and the
# real prompt comes from scripts/analyze_start_picture.py -> WORKDIR/motion_prompt.txt (see PROMPT_TEMPLATE.md).
MOTION="Looks straight into the camera lens the whole time, warm and confident; the phone arm stays still, and the free hand makes small slow open-palm gestures, five relaxed fingers."
EXPRESSIVENESS=${EXPRESSIVENESS:-high}
[ -s "$W/motion_prompt.txt" ] && MOTION=$(cat "$W/motion_prompt.txt")
# Standing rule: no render without a PASSED start-picture analysis (eyes into the lens, hands, phone, background).
if [ -z "${SKIP_PICTURE_ANALYSIS:-}" ]; then
  if [ ! -s "$W/picture_analysis.json" ]; then
    echo "STOP: run scripts/analyze_start_picture.py LOOK.jpg --look Lxx --json $W/picture_analysis.json --prompt-out $W/motion_prompt.txt first" >&2; exit 3
  fi
  if [ "$(jq '.problems | length' "$W/picture_analysis.json")" != "0" ]; then
    echo "STOP: start picture failed its analysis: $(jq -c .problems "$W/picture_analysis.json")" >&2; exit 3
  fi
  [ -s "$W/motion_prompt.txt" ] || { echo "STOP: write $W/motion_prompt.txt from the analysis" >&2; exit 3; }
fi
ASSET=$(jq -r '.data.asset_id // empty' "$W/voice_asset.json" 2>/dev/null || true)
if [ -n "$ASSET" ]; then
  jq -n --arg t "$TITLE" --arg a "$AV" --arg s "$ASSET" --arg m "$MOTION" --arg x "$EXPRESSIVENESS" \
    '{type:"avatar",title:$t,avatar_id:$a,audio_asset_id:$s,engine:{type:"avatar_iv"},expressiveness:$x,motion_prompt:$m,aspect_ratio:"9:16",fit:"cover",resolution:"720p"}' > "$W/request.json"
else
  [ -s "$W/script.txt" ] || { echo "need $W/script.txt (the words the agent says)" >&2; exit 2; }
  S=$(tr '\n' ' ' < "$W/script.txt" | sed 's/  */ /g;s/ $//')
  jq -n --arg t "$TITLE" --arg a "$AV" --arg s "$S" --arg v "$VOICE" --arg m "$MOTION" --arg x "$EXPRESSIVENESS" \
    '{type:"avatar",title:$t,avatar_id:$a,script:$s,voice_id:$v,engine:{type:"avatar_iv"},expressiveness:$x,motion_prompt:$m,aspect_ratio:"9:16",fit:"cover",resolution:"720p"}' > "$W/request.json"
fi
BEFORE=$(hg_credits)
if [ "$DRY" = "--dry-run" ]; then
  echo "[dry-run] request.json:"; cat "$W/request.json"; echo "[dry-run] words: $(wc -w < "$W/script.txt" 2>/dev/null || echo audio)  credits now: $BEFORE"; exit 0
fi
[ "$BEFORE" != "unknown" ] && [ "$BEFORE" -lt "${AGENT_MIN_CREDITS:-40}" ] && { echo "balance $BEFORE is under ${AGENT_MIN_CREDITS:-40}: not rendering, tell the owner" >&2; exit 3; }
# Standing rule: a second render is allowed ONLY when the pre-post check failed and editing cannot fix it:
# RERENDER_REASON="what qa_video.py found" moves the old render to render_try1/ and renders once more (max 2 per video).
if [ -s "$W/render.json" ] && jq -e '.data.video_url' "$W/render.json" >/dev/null 2>&1; then
  if [ -n "${RERENDER_REASON:-}" ] && [ ! -d "$W/render_try1" ]; then
    mkdir -p "$W/render_try1"; mv "$W/render.json" "$W/avatar_raw.mp4" "$W/render_try1/" 2>/dev/null; cp "$W/request.json" "$W/render_try1/" 2>/dev/null
    echo "$(date -Is) re-render: $RERENDER_REASON" >> "$W/notes.txt"
  else
    echo "$W already has a finished render. A re-render needs RERENDER_REASON (a failed pre-post check) and only one is allowed." >&2; exit 4
  fi
fi
hg video create -d "$W/request.json" --wait --timeout 15m > "$W/render.json" 2> "$W/render_err.txt"
URL=$(jq -r '.data.video_url // empty' "$W/render.json")
[ -n "$URL" ] || { echo "render failed: $(jq -c '.data.status, .error' "$W/render.json" 2>/dev/null) (see render_err.txt)" >&2; exit 1; }
curl -sfL -o "$W/avatar_raw.mp4" "$URL"
AFTER=$(hg_credits)
echo "credits before $BEFORE after $AFTER" | tee "$W/credits.txt"
ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of compact "$W/avatar_raw.mp4"
