#!/usr/bin/env bash
# Soundboard: 19 short sound effects (whoosh, pop, click, riser, impact, glitch, chime...) for your edits.
# The files come from HyperFrames' bundled library (Pixabay Content License, see soundboard/CREDITS.md). They are
# downloaded from the HyperFrames repo at a pinned commit, not stored in this kit.
#
# Usage:
#   soundboard.sh install                       download the 19 effects into $AGENT_HOME/soundboard (once)
#   soundboard.sh list                          name, length and when to use each effect
#   soundboard.sh add IN.mp4 OUT.mp4 NAME@SEC[:VOL] [NAME@SEC[:VOL] ...]
#        mix effects UNDER the video's own audio, e.g.
#        soundboard.sh add final.mp4 final_sfx.mp4 whoosh@3.9 pop@4.2:0.3 riser@20.0:0.25
#        VOL defaults to 0.35 (effects sit under the voice). Video is copied, audio re-encoded, loudness kept at -14 LUFS.
# Rules: one or two effects per card change at most; never over a quote or a lyric; a riser ends ON the hit
# (start it at hit time minus its length, see list).
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
HF_COMMIT=1116077dabf5bacde60e566578e85068e6777b17
BASE="https://raw.githubusercontent.com/heygen-com/hyperframes/$HF_COMMIT/skills/media-use/audio/assets/sfx"
SB="${AGENT_SOUNDBOARD:-$AGENT_HOME/soundboard}"
MAN="$KIT_HOME/soundboard/manifest.json"
cmd=${1:-list}; shift || true
case "$cmd" in
  install)
    mkdir -p "$SB"
    for f in $(jq -r '.[].file' "$MAN"); do
      [ -s "$SB/$f" ] && continue
      curl -fsSL --retry 2 -o "$SB/$f" "$BASE/$f" || { echo "download failed: $f" >&2; exit 1; }
    done
    cp "$MAN" "$KIT_HOME/soundboard/CREDITS.md" "$SB/"
    echo "soundboard ready: $(ls "$SB"/*.mp3 | wc -l) effects in $SB";;
  list)
    jq -r 'to_entries[] | "\(.key)\t\(.value.duration)s\t\(.value.description)"' "$MAN" | column -t -s $'\t';;
  add)
    IN=${1:?input video}; OUT=${2:?output video}; shift 2
    [ $# -gt 0 ] || { echo "give at least one NAME@SEC" >&2; exit 2; }
    args=(-i "$IN"); fc=""; mix="[0:a]"; n=1
    for cue in "$@"; do
      name=${cue%%@*}; rest=${cue#*@}; at=${rest%%:*}; vol=0.35; [ "$rest" != "$at" ] && vol=${rest#*:}
      file=$(jq -r --arg k "$name" '.[$k].file // empty' "$MAN")
      [ -n "$file" ] && [ -s "$SB/$file" ] || { echo "unknown or missing effect '$name' (run: soundboard.sh install / list)" >&2; exit 2; }
      ms=$(python3 -c "print(int(round(float('$at')*1000)))")
      args+=(-i "$SB/$file")
      fc+="[$n:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=$vol,adelay=$ms|$ms[s$n];"
      mix+="[s$n]"; n=$((n+1))
    done
    fc+="[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a0];"
    mix=${mix/\[0:a\]/[a0]}
    fc+="${mix}amix=inputs=$n:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    ffmpeg -v error -y "${args[@]}" -filter_complex "$fc" -map 0:v -map "[a]" -c:v copy -c:a aac -ar 48000 -b:a 192k -movflags +faststart "$OUT"
    echo "wrote $OUT";;
  *) echo "usage: soundboard.sh install | list | add IN OUT NAME@SEC[:VOL]..." >&2; exit 2;;
esac
