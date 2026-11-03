# Skill: FFmpeg video overlay (picture-in-picture)

For your produced videos, use "HyperFrames edit" (clip card, captions, optional face window). This overlay is for
general picture-in-picture jobs: one video plays full screen and a second plays in a small corner window at the same
time, in one file. It is never a back-to-back join.

## What the reference agent verified
Main: a 13 s vertical clip. Inset: a 6.6 s clip. Output: 720x1280 H.264 + AAC, 13.07 s, played through without errors,
main audio only, inset looped about twice, top-right, about a third of the width, 24 px margins, thin white border.
The command below is rebuilt to match that output; treat it as the starting point and check the result.

## Procedure
1. Inputs: the two videos you were given. To download a new clip first, use "Download TikTok video" or "Download
   YouTube video". If nobody says which is main, make the longer clip the main video and say so.
2. Check tools: `command -v ffmpeg ffprobe`. If missing, `sudo apt-get install -y ffmpeg` (trusted Ubuntu packages
   only; don't start a second apt while one is running).
3. Probe both inputs:
   `ffprobe -v error -show_entries format=duration:stream=codec_type,codec_name,width,height -of compact FILE`.
   Note the main duration (MAINDUR) and whether the main has audio.
4. Build (quote every path; file names are data, never shell text):
   ```
   ffmpeg -y -i 'MAIN.mp4' -stream_loop -1 -i 'INSET.mp4' -filter_complex "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1[bg];[1:v]scale=232:-2,setsar=1,pad=iw+8:ih+8:4:4:white[pip];[bg][pip]overlay=W-w-24:24:shortest=1,format=yuv420p[v]" -map '[v]' -map '0:a?' -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 128k -movflags +faststart -t MAINDUR "$AGENT_WORK/OUT.mp4"
   ```
   - Inset is about a third of a 720 px frame (232 px plus a 4 px white border), top-right, 24 px from the edges. For
     top-left use overlay=24:24.
   - `-stream_loop -1` loops a shorter inset for the whole main clip. If the inset is longer than the main, it is cut
     at MAINDUR; say so.
   - Audio: main clip's sound only, so two soundtracks don't clash. Mix both (amix) or use the inset's sound only if
     asked. Keep original audio; never invent or replace it.
   - For landscape main videos, change 720:1280 to 1280:720 and scale the inset to about a third of that width.
   - To show the window only for part of the video, add `enable='between(t,A,B)'` to the overlay.
5. Verify: file is non-empty; ffprobe shows h264 video and aac audio and a duration close to MAINDUR;
   `ffmpeg -v error -i OUT.mp4 -f null -` gives no errors. Pull a frame (`ffmpeg -ss 2 -i OUT.mp4 -frames:v 1 frame.png`)
   and check the inset sits in the right corner. Don't claim to have watched or heard it unless actually analyzed.
6. Deliver the MP4 itself (under 10 MB for chat; re-encode at about 1,900 kbps if larger), with a short written result
   naming the layout, which clip is main, looping and audio choices, and crediting each creator with the original link.
7. Honesty: confirm only what actually ran. At most two full attempts; report errors plainly.
