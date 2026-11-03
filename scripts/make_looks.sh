#!/usr/bin/env bash
# AVATAR ROUTE ONLY. Generate new looks of the agent (photo looks in its own HeyGen avatar group) from a batch file, using a text prompt
# with the agent's main close-up (AGENT_REF_LOOK_ID) as the identity reference. Bills the plan you signed in to via `hg`.
# Cost measured on the reference agent: 1 credit per look.
# Usage: make_looks.sh BATCH.json [--dry-run]
#   BATCH.json: [{"code":"L31","style":"selfie|propped|portrait","phone_side":"left|right|none","outfit":"...","framing":"...",
#                 "background":"...","good_for":"...","look":"<outfit, setting, phone hand, free hand, framing, expression>"}]
# The whole prompt (PRE + look + POST) must be at most 1000 characters (HeyGen limit): keep "look" under about 640.
# Writes looks/req_CODE.json, looks/resp_CODE.json, looks/previews/CODE.jpg and appends to looks/catalog.json, then runs
# face_check.py (keep 0.60+) and pose_check.py (mouth must be slightly open, hands sane).
#
# Lesson from the reference agent: new looks are SELFIE / VLOG looks: phone held at arm's length in one hand (phone itself out
# of frame), the other hand free and mid-gesture, MOUTH SLIGHTLY OPEN mid-word, expressive face, an everyday background
# that fits a topic. The old POST line said "mouth closed ... hands resting", which made renders stiff.
# Gate:
#   ALLOW_NEW_LOOKS=yes   any batch size (only when the owner explicitly asks for new looks)
#   ALLOW_NEW_LOOKS=one   exactly ONE look: what a video run may make when no existing selfie look fits the topic
#   ALLOW_NEW_LOOKS=pair  exactly TWO looks: standing rule: a new start picture as a matching pair,
#                         full frame + close-up of the upper body and free hand, both checked by hand_check.py
set -euo pipefail
case "${ALLOW_NEW_LOOKS:-}" in yes|one|pair) ;; *) echo "make_looks.sh is gated: ALLOW_NEW_LOOKS=one (one topic look in a video run) or =yes (owner asked for a batch)." >&2; exit 5;; esac
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
D=$AGENT_LOOKS; B=${1:?batch.json}; DRY=${2:-}
REF=${AGENT_REF_LOOK_ID:?set AGENT_REF_LOOK_ID in settings.env (your main close-up look id)}   # identity reference
mkdir -p "$D/previews"
PRE="Same person as in the reference image: identical face, skin tone, eyes, nose, lips and hairstyle."
POST_SELFIE="Face sharp, well lit, eyes to the lens. Mouth slightly open mid-word, lips parted with a hint of top teeth, lively natural expression, not a posed smile. Candid phone front-camera vlog photo, natural skin, realistic hands with five fingers, no text."
POST_PORTRAIT="Face sharp, well lit, eyes to the camera. Mouth slightly open mid-word, lively natural expression, one hand free and visible. Realistic photo, natural skin, realistic hands with five fingers."
N=$(jq length "$B")
if [ "${ALLOW_NEW_LOOKS}" = one ] && [ "$N" -ne 1 ]; then echo "ALLOW_NEW_LOOKS=one allows exactly one look; batch has $N" >&2; exit 5; fi
if [ "${ALLOW_NEW_LOOKS}" = pair ] && [ "$N" -ne 2 ]; then echo "ALLOW_NEW_LOOKS=pair allows exactly two looks (full + close-up); batch has $N" >&2; exit 5; fi
[ -f "$D/catalog.json" ] || echo '[]' > "$D/catalog.json"
CR=$(hg_credits)
echo "looks to make: $N, credits now: $CR, expected cost: about $N"
[ "$CR" != unknown ] && [ "$CR" -lt $((${AGENT_MIN_CREDITS:-40} + N)) ] && { echo "balance $CR is too low: keep ${AGENT_MIN_CREDITS:-40} for the render; not making looks" >&2; exit 3; }
[ "$DRY" = "--dry-run" ] && { jq -r '.[] | "\(.code)  [\(.style // "portrait")/phone \(.phone_side // "-")]  \(.outfit) | \(.framing) | \(.background)"' "$B"; exit 0; }
IDS=()
for i in $(seq 0 $((N-1))); do
  E=$(jq -c ".[$i]" "$B"); C=$(jq -r .code <<<"$E"); ST=$(jq -r '.style // "portrait"' <<<"$E")
  if jq -e --arg c "$C" 'any(.[]; .code==$c)' "$D/catalog.json" >/dev/null; then echo "$C already in catalog, skipped"; continue; fi
  POST=$POST_SELFIE; [ "$ST" = portrait ] && POST=$POST_PORTRAIT
  jq -n --argjson e "$E" --arg ref "$REF" --arg pre "$PRE" --arg post "$POST" \
    '{type:"prompt", name:(env.AGENT_NAME+" - "+$e.code+" "+$e.outfit+" / "+$e.background), avatar_id:$ref, aspect_ratio:"9:16", prompt:($pre+" "+$e.look+" "+$post)}' > "$D/req_$C.json"
  L=$(jq -r '.prompt|length' "$D/req_$C.json"); [ "$L" -le 1000 ] || { echo "$C: prompt is $L characters, HeyGen allows 1000: shorten the look text" >&2; continue; }
  hg avatar create -d "$D/req_$C.json" --idempotency-key "$AGENT_SLUG-look-$C-$(date +%Y%m%d)" > "$D/resp_$C.json" || true
  ID=$(jq -r '.data.avatar_item.id // empty' "$D/resp_$C.json")
  [ -n "$ID" ] || { echo "$C: create failed: $(jq -c '.error // .' "$D/resp_$C.json" | head -c 300)" >&2; continue; }
  IDS+=("$C:$ID"); echo "$C submitted as $ID"
done
for pair in "${IDS[@]}"; do
  C=${pair%%:*}; ID=${pair#*:}
  for t in $(seq 1 60); do S=$({ hg avatar looks get "$ID" || echo '{"data":{"status":"processing"}}'; } | tee "$D/look_$C.json" | jq -r .data.status); [ "$S" = processing ] || break; sleep 10; done
  if [ "$S" = completed ]; then
    curl -sfL -o "$D/previews/$C.jpg" "$(jq -r .data.preview_image_url "$D/look_$C.json")"
    E=$(jq -c --arg c "$C" '.[] | select(.code==$c)' "$B")
    jq --argjson e "$E" --arg id "$ID" --arg pv "previews/$C.jpg" '. + [($e | del(.look)) + {look_id:$id, status:"pending_check", created:(now|strftime("%Y-%m-%d")), banner_y:150, preview:$pv}]' "$D/catalog.json" > "$D/catalog.tmp" && mv "$D/catalog.tmp" "$D/catalog.json"
    echo "$C completed"
  else echo "$C: $S $(jq -c .data.error "$D/look_$C.json")" >&2; fi
done
echo "credits now: $(hg_credits)"
cd "$D"
P=$(for p in "${IDS[@]}"; do f="previews/${p%%:*}.jpg"; [ -f "$f" ] && echo "$f"; done)
[ -n "$P" ] || exit 0
python3 $AGENT_SCRIPTS/face_check.py $P 2>/dev/null
python3 $AGENT_SCRIPTS/pose_check.py $P 2>/dev/null | grep -v '^INFO\|^WARNING'
echo "New looks are status pending_check. Keep a look only if face cos >= 0.60, mouth is slightly open (0.03-0.12), no WARN,"
echo "and the preview looks right; then set status active, face_match, mouth and banner_y in catalog.json (or retired)."
