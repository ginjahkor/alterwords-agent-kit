# Soundboard

19 short sound effects for edits: whooshes for card changes, pops and clicks for text, a riser and bass impacts for a
reveal, glitches for hard cuts, chimes and pings for a light beat, typing for on-screen text.

- `manifest.json`: every effect with its length and when to use it (the same index HyperFrames uses).
- `CREDITS.md`: where the sounds come from (Pixabay Content License).
- The audio files are not in this repo. `bash scripts/soundboard.sh install` downloads them from the HyperFrames repo
  at a pinned commit into `$AGENT_HOME/soundboard`. install.sh runs it for you.

## Use

```
bash scripts/soundboard.sh list
bash scripts/soundboard.sh add POSTDIR/final.mp4 POSTDIR/final_sfx.mp4 whoosh@3.9 pop@4.2:0.3
```

Rules: effects sit under your voice (default volume 0.35), one or two per card change at most, never over a quote or a
lyric, and a riser ends on the hit, so start it at the hit time minus its length. Run qa_video.py and a loudness check
again after adding effects.

HyperFrames can also search Openverse for a specific effect (CC0 and CC BY only) with
`hyperframes media-use resolve --type sfx`; credit any CC BY sound in your caption.
