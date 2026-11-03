#!/usr/bin/env bash
# Makes the plain test-pattern videos each HyperFrames layout uses when you render it as it is.
# Run once after cloning: bash templates/make_test_assets.sh
set -euo pipefail
cd "$(dirname "$0")/hyperframes"
mk() { # out size with_audio
  mkdir -p "$(dirname "$1")"
  if [ "${3:-}" = a ]; then
    ffmpeg -y -v error -f lavfi -i "testsrc2=size=$2:rate=30:duration=4" -f lavfi -i "sine=frequency=440:duration=4" \
      -c:v libx264 -pix_fmt yuv420p -crf 30 -c:a aac -b:a 64k -shortest "$1"
  else
    ffmpeg -y -v error -f lavfi -i "testsrc2=size=$2:rate=30:duration=4" -c:v libx264 -pix_fmt yuv420p -crf 30 "$1"
  fi
}
mk clip_card/assets/bg.mp4 270x480
mk clip_card/assets/fg.mp4 854x480 a
mk talking_head_captions/assets/fg.mp4 270x480
mk title_card/assets/fg.mp4 270x480 a
mk word_captions/assets/fg.mp4 270x480 a
echo "test assets made"
