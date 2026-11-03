#!/usr/bin/env bash
# Make ONE new selfie look that fits today's topic, when pick_look.py says TOPIC_MATCH=0.
# At most one per video run, before the single render. Costs about 1 HeyGen credit (Creator plan via `hg`).
# Usage: make_topic_look.sh "OUTFIT" "BACKGROUND (short)" "good_for words" "LOOK TEXT" [left|right|none]
#   LOOK TEXT (max ~600 characters): outfit, the setting that fits the topic, then exactly this pose pattern:
#   "Selfie taken with her phone's front camera: the arm holding the phone reaches toward the camera from the left edge
#    of the picture, the phone itself is outside the frame. Her other hand, on the right side of the picture, is raised at
#    chest height, palm open, fully inside the frame, mid-gesture. Chest-up framing at arm's length, a little space above
#    her hair. She looks <one expression that fits the take>, talking, not grinning."
#   Swap left/right to the opposite of the last video's phone hand. For a propped-phone look use "none" and write
#   "She has propped her phone up on <surface> to film herself ... one hand raised mid-explanation".
# On success prints LOOK_CODE= LOOK_ID= BANNER_Y= (eval it) and exits 0. If the look fails the checks (face < 0.60,
# mouth closed or wide, odd hands, visible phone, second big person) it is retired and the script exits 4: then use the
# look pick_look.py chose. Never try a second one in the same run.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
S=$AGENT_SCRIPTS; D=$AGENT_LOOKS
OUT=${1:?outfit}; BG=${2:?background}; GF=${3:?good_for}; LOOK=${4:?look text}; SIDE=${5:-left}
N=$(jq -r '[.[].code | select(test("^L[0-9]+$")) | ltrimstr("L") | tonumber] | max + 1' "$D/catalog.json")
C=$(printf 'L%02d' "$N")
ST=selfie; [ "$SIDE" = none ] && ST=propped
B=$(mktemp --suffix=.json)
jq -n --arg c "$C" --arg o "$OUT" --arg b "$BG" --arg g "$GF" --arg l "$LOOK" --arg s "$SIDE" --arg st "$ST" \
  '[{code:$c, style:$st, phone_side:$s, outfit:$o, framing:"topic selfie, chest-up, arm'"'"'s length", background:$b, good_for:$g, look:$l, made_for_topic:true}]' > "$B"
cp "$B" "$D/topic_$C.json"
ALLOW_NEW_LOOKS=one bash "$S/make_looks.sh" "$B" >&2
R=$(python3 "$S/accept_looks.py" "$C" 2>/dev/null | tail -1)
echo "$(date -Is) $C $R" >> "$D/topic_looks.log"
echo "$R" >&2
if [[ "$R" == *$'\tactive\t'* ]]; then
  jq -r --arg c "$C" '.[] | select(.code==$c) | "LOOK_CODE=\(.code)\nLOOK_ID=\(.look_id)\nBANNER_Y=\(.banner_y)\nLOOK_STYLE=\(.style)\nPHONE_SIDE=\(.phone_side)"' "$D/catalog.json"
else
  echo "topic look $C did not pass; use the pick_look.py choice" >&2; exit 4
fi
