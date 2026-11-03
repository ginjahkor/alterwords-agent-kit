#!/usr/bin/env bash
# Export the finished video: join the segments, match the inserted clip's loudness to your voice, normalise to
# -14 LUFS, write the post file and (when needed) a chat copy under 10 MB, then print the checks.
# Usage: export_final.sh POSTDIR SEG1.mp4 [SEG2.mp4 ...] [--clip-gain N]
#   Segments are joined in order (e.g. segA = voice part 1, segB = source clip with its own sound, segC = voice part 2).
#   --clip-gain N  dB to apply to every segment named *insert* or *clip* (default: measured automatically against the
#                  first segment so they land within 1 LU of your voice).
# Writes POSTDIR/final.mp4 (1080x1920 H.264/AAC, faststart), POSTDIR/final_chat.mp4 if final.mp4 > 10 MB,
# POSTDIR/export_report.txt.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
D=${1:?post dir}; shift
SEGS=(); GAIN=""
while [ $# -gt 0 ]; do case "$1" in --clip-gain) GAIN=$2; shift 2;; *) SEGS+=("$1"); shift;; esac; done
[ ${#SEGS[@]} -ge 1 ] || { echo "give at least one segment" >&2; exit 2; }
lufs() { ffmpeg -nostats -i "$1" -af ebur128 -f null - 2>&1 | awk '/Integrated loudness/{f=1} f&&/I:/{print $2; exit}'; }
REF=$(lufs "${SEGS[0]}")
args=(); fc=""; cat=""; i=0
for s in "${SEGS[@]}"; do
  args+=(-i "$s")
  g=0
  case "$(basename "$s")" in *insert*|*clip*)
    if [ -n "$GAIN" ]; then g=$GAIN; else L=$(lufs "$s"); g=$(python3 -c "print(round(float('$REF')-float('$L'),1))"); fi
    echo "clip $(basename "$s"): gain ${g} dB (voice ${REF} LUFS)";;
  esac
  fc+="[$i:v]scale=1080:1920,setsar=1,fps=30,format=yuv420p[v$i];[$i:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=${g}dB[a$i];"
  cat+="[v$i][a$i]"; i=$((i+1))
done
fc+="${cat}concat=n=$i:v=1:a=1[v][a0];[a0]loudnorm=I=-14:TP=-1.5:LRA=11[a]"
ffmpeg -v error -y "${args[@]}" -filter_complex "$fc" -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset medium \
  -pix_fmt yuv420p -movflags +faststart -c:a aac -ar 48000 -b:a 192k "$D/final.mp4"
SIZE=$(stat -c %s "$D/final.mp4")
if [ "$SIZE" -gt 10000000 ]; then
  ffmpeg -v error -y -i "$D/final.mp4" -c:v libx264 -b:v 1900k -maxrate 2200k -bufsize 4000k -pix_fmt yuv420p \
    -movflags +faststart -c:a aac -b:a 128k "$D/final_chat.mp4"
fi
{
  echo "final.mp4: $(ffprobe -v error -show_entries stream=codec_name,width,height:format=duration,size -of compact=p=0:nk=1 "$D/final.mp4" | tr '\n' ' ')"
  echo "loudness: $(lufs "$D/final.mp4") LUFS (target -14)"
  [ -f "$D/final_chat.mp4" ] && echo "final_chat.mp4: $(stat -c %s "$D/final_chat.mp4") bytes"
  ffmpeg -v error -i "$D/final.mp4" -f null - 2>&1 | head -3 | sed 's/^/decode error: /'
} | tee "$D/export_report.txt"
echo "next: python3 scripts/qa_video.py $D/final.mp4 --sheet $D/qa_final_sheet.jpg --json $D/qa_final.json"
