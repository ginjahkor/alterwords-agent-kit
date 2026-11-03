#!/usr/bin/env bash
# selftest.sh - end-to-end test on a real public clip, no keys and no credits needed.
# download (YouTube, through WARP) -> analyze (Whisper words, scenes, loudness) -> HyperFrames edit
# (clip card + word-by-word captions) -> FFmpeg checks -> face/hand models load.
# Usage: bash selftest.sh [YOUTUBE_URL]     (default: "Me at the zoo", the first YouTube video, 19 s, public)
# Exit 0 = every step passed. Output in $AGENT_WORK/_selftest/.
set -uo pipefail
KIT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; export KIT_HOME
. "$KIT_HOME/scripts/env.sh"
S="$KIT_HOME/scripts"; URL=${1:-https://www.youtube.com/watch?v=jNQXAC9IVRw}
T="$AGENT_WORK/_selftest"; rm -rf "$T"; mkdir -p "$T"
PASS=0; FAIL=0
ok() { echo "PASS  $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL  $1"; FAIL=$((FAIL+1)); }

echo "1/6 tools"
for t in ffmpeg ffprobe yt-dlp deno node hyperframes jq tesseract; do command -v $t >/dev/null && ok "$t found" || bad "$t missing"; done

echo "2/6 download $URL"
if bash "$S/download_youtube.sh" "$URL" clip "$T" > "$T/download.log" 2>&1 && [ -s "$T/clip.mp4" ]; then
  ok "YouTube download ($(du -h "$T/clip.mp4" | cut -f1), $(cut -d'|' -f2,5 "$T/clip_meta.txt" 2>/dev/null))"
else bad "YouTube download (see $T/download.log; try: bash scripts/warp_up.sh --restart)"; fi

echo "3/6 analyze (first run downloads the Whisper model, a few minutes)"
if [ -s "$T/clip.mp4" ] && python3 "$S/analyze_source.py" "$T/clip.mp4" --out "$T/analysis" --speech --lens 6 > "$T/analyze.log" 2>&1 \
   && [ -s "$T/analysis/words.json" ]; then
  ok "analysis: $(jq length "$T/analysis/words.json") timed words, timeline.md written"
else bad "analysis (see $T/analyze.log)"; fi

echo "4/6 HyperFrames edit (clip card + word-by-word captions)"
if [ -s "$T/analysis/words.json" ] && python3 "$S/hf_build.py" --clip "$T/clip.mp4" --words "$T/analysis/words.json" --layout card \
     --pill "SELF TEST" --title "KIT WORKS" --credit "Clip: jawed (YouTube)" --out "$T/edit.mp4" --project "$T/hf" > "$T/hf.log" 2>&1 \
   && [ -s "$T/edit.mp4" ]; then ok "HyperFrames render"; else bad "HyperFrames render (see $T/hf.log)"; fi

echo "5/6 FFmpeg checks on the edit"
if [ -s "$T/edit.mp4" ]; then
  INFO=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 "$T/edit.mp4")
  [ "$INFO" = "h264,1080,1920" ] && ok "edit is H.264 1080x1920" || bad "edit format is $INFO"
  ERR=$(ffmpeg -v error -i "$T/edit.mp4" -f null - 2>&1 | wc -l); [ "$ERR" = 0 ] && ok "clean decode" || bad "$ERR decode errors"
  ffprobe -v error -select_streams a -show_entries stream=codec_name -of csv=p=0 "$T/edit.mp4" | grep -q aac && ok "audio present" || bad "no audio"
else bad "no edit to check"; fi

echo "6/6 vision models load"
if python3 - "$AGENT_MODELS" <<'PY' > "$T/models.log" 2>&1
import sys, os, cv2
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
D = sys.argv[1]
cv2.FaceDetectorYN.create(os.path.join(D, "yunet.onnx"), "", (320, 320))
cv2.FaceRecognizerSF.create(os.path.join(D, "sface.onnx"), "")
cv2.dnn.readNet(os.path.join(D, "yolox_s.onnx"))
for t in ("face_landmarker.task", "hand_landmarker.task"):
    o = (vision.FaceLandmarkerOptions if t.startswith("face") else vision.HandLandmarkerOptions)(base_options=mpt.BaseOptions(model_asset_path=os.path.join(D, t)))
    (vision.FaceLandmarker if t.startswith("face") else vision.HandLandmarker).create_from_options(o)
print("models ok")
PY
then ok "face, hand and object models load"; else bad "models (see $T/models.log)"; fi

echo
echo "Self-test: $PASS passed, $FAIL failed. Output: $T"
[ $FAIL = 0 ]
