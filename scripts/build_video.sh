#!/usr/bin/env bash
# Edit the final agent video: hook, listening pause, take. FFmpeg only, no credits.
# Usage: build_video.sh AVATAR_RAW CLIP BANNER STILL HOOK_SEC PAUSE_SEC OUT [CLIP_START_SEC]
#   AVATAR_RAW  HeyGen render (voice = hook + silence + take); its length sets the total
#   CLIP        trend clip (H.264 MP4)
#   BANNER      1080x200 PNG from make_banner.py
#   STILL       bright frame of the clip (analyze_clip.py --still) for the hook-section window
#   HOOK_SEC    hook length (HOOK_SEC from timings.env), PAUSE_SEC the silent gap
#   CLIP_START  where the song should start in the pause (default 0)
# Layout: hook = avatar full + clip still in white-bordered window bottom right (x740,y1116, 300x524);
# pause = clip full at full volume + avatar window bottom left (x40,y968, 372x652);
# take = avatar full + clip window bottom right, song ducked to 12% over 0.6 s; banner at y150 all the way (override with BANNER_Y=... for looks whose face sits high, see looks/catalog.json).
# Keeps the file under 10 MB by raising CRF from 26 in steps of 2.
set -euo pipefail
S=${1:?avatar raw}; C=${2:?clip}; B=${3:?banner}; ST=${4:?still}; H=${5:?hook sec}; P=${6:?pause sec}; OUT=${7:?out}; CS=${8:-0}
P2=$(python3 -c "print(round($H+$P,3))")
HMS=$(python3 -c "print(int(round($H*1000)))")
TOTAL=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$S")
LIMIT=10000000
# HANDHELD=1 (default for selfie/vlog looks): my full-screen layer drifts a few pixels like a phone
# held at arm's length (scaled 3.7% up, crop offsets from slow sine waves, max about 18 px). The banner and windows stay still.
# HANDHELD=0 for the old posed portrait looks.
if [ "${HANDHELD:-1}" = 1 ]; then SV='fps=25,scale=1120:1992,crop=1080:1920:20+12*sin(t*1.1)+6*sin(t*2.7):36+10*sin(t*0.9+1)+5*sin(t*2.3),setsar=1'; else SV='fps=25,scale=1080:1920,setsar=1'; fi
BANNER_Y=${BANNER_Y:-150}   # headline y; set from the look (looks/catalog.json banner_y) when the face sits high in the frame
crf=26
while :; do
  ffmpeg -v error -y -i "$S" -ss "$CS" -i "$C" -loop 1 -i "$B" -loop 1 -framerate 25 -t "$H" -i "$ST" -filter_complex "
[0:v]${SV},split=2[sF][s0];[s0]scale=360:640,pad=372:652:6:6:white[sS];
[3:v]scale=1080:1920,setsar=1,fps=25,format=yuv420p[st];[1:v]fps=25,scale=1080:1920,setsar=1,format=yuv420p[fc];[st][fc]concat=n=2:v=1:a=0,split=2[fF][f0];[f0]scale=288:512,pad=300:524:6:6:white[fS];
[sF][fS]overlay=x=740:y=1116[A];
[fF][sS]overlay=x=40:y=968[Bv];
[A][Bv]overlay=0:0:enable='between(t,$H,$P2)'[Cv];
[Cv][2:v]overlay=0:${BANNER_Y}:shortest=1,format=yuv420p[v];
[0:a]aresample=44100,volume=1.6[va];
[1:a]aresample=44100,adelay=$HMS|$HMS,volume='if(lt(t,$P2-0.2),1,if(lt(t,$P2+0.4),1-0.88*(t-($P2-0.2))/0.6,0.12))':eval=frame[ma];
[va][ma]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]" \
  -map "[v]" -map "[a]" -t "$TOTAL" -c:v libx264 -preset slow -crf "$crf" -maxrate 1900k -bufsize 3800k -profile:v high -level 4.1 \
  -c:a aac -b:a 128k -ar 44100 -movflags +faststart "$OUT"
  size=$(stat -c %s "$OUT")
  echo "crf $crf -> $size bytes"
  [ "$size" -lt "$LIMIT" ] && break
  crf=$((crf+2)); [ $crf -gt 34 ] && { echo "still over 10 MB at crf 34" >&2; exit 1; }
done
echo "built $OUT (hook 0-$H, pause $H-$P2, take $P2-$TOTAL)"
