#!/usr/bin/env bash
# Check a finished video: codecs, size, clean decode, loudness per segment.
# Usage: verify_video.sh OUT.mp4 HOOK_SEC PAUSE_SEC
set -euo pipefail
F=${1:?video}; H=${2:?hook}; P=${3:?pause}
P2=$(python3 -c "print($H+$P)")
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate -show_entries format=duration,size -of compact "$F"
size=$(stat -c %s "$F"); [ "$size" -lt 10000000 ] && echo "size OK ($size bytes)" || echo "SIZE OVER 10 MB ($size)"
ffmpeg -v error -i "$F" -f null - && echo "decode OK"
seg() { ffmpeg -v info -ss "$1" -t "$2" -i "$F" -vn -af volumedetect -f null - 2>&1 | grep -E 'mean_volume' | sed "s/.*mean_volume/$3 mean_volume/"; }
seg 0 "$H" hook
seg "$H" "$P" pause
seg "$P2" 60 take
echo "Expect: pause loudest; hook and take about -16 dB mean. Watch it before claiming it looks right."
