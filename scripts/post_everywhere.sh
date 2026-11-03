#!/usr/bin/env bash
# Default for every video: post it to TikTok, Instagram (Reel) and X through Buffer,
# each with its own caption file, AI disclosure on, one hosted link reused for all three.
# Only run after the owner said yes to this video.
# Usage: post_everywhere.sh POSTDIR [--only tiktok,instagram,x] [--dry-run]
#   Needs POSTDIR/final.mp4 and POSTDIR/caption.txt (TikTok), caption_instagram.txt, caption_x.txt.
#   Order and spacing: TikTok now, Instagram now, X now (they are different audiences, so posting together is fine).
#   To space them out, run buffer_post.sh per platform with --due TIME instead.
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
D=${1:?post dir}; shift
ONLY=tiktok,instagram,x; DRY=""
while [ $# -gt 0 ]; do case "$1" in --only) ONLY=$2; shift 2;; --dry-run) DRY=--dry-run; shift;; *) echo "unknown arg $1" >&2; exit 2;; esac; done
for p in ${ONLY//,/ }; do
  case $p in tiktok) C=$D/caption.txt;; instagram) C=$D/caption_instagram.txt;; x) C=$D/caption_x.txt;; *) echo "bad platform $p" >&2; exit 2;; esac
  [ -f "$C" ] || { echo "missing $C" >&2; exit 2; }
done
for p in ${ONLY//,/ }; do
  case $p in tiktok) C=$D/caption.txt;; instagram) C=$D/caption_instagram.txt;; x) C=$D/caption_x.txt;; esac
  echo "=== $p ==="
  "$AGENT_SCRIPTS/buffer_post.sh" "$D/final.mp4" "$C" "$D" --platform "$p" --mode shareNow $DRY || echo "!!! $p failed, carrying on with the others" >&2
done
