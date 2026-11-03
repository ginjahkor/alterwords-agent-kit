# Install profiles

Every tool the kit uses: what it does, the version the reference agent runs, how install.sh installs it, how to check
it, and what to do when it breaks. `bash install.sh` installs all of it (add `--with-avatar` for the avatar tools);
`bash selftest.sh` checks it. No tool here needs a key except Buffer (posting), HeyGen (avatar route) and your voiceover
provider, and those keys go in settings.env or the tool's own sign-in, never in this repo.

## System (apt)

| Tool | Version tested | Used for | Check |
|---|---|---|---|
| FFmpeg + ffprobe | 8.0.1 | every cut, overlay, mix, export, probe | `ffmpeg -version` |
| jq | 1.8.1 | reading JSON from Buffer, HeyGen and the manifests | `jq --version` |
| tesseract | 5.5.0 | reading on-screen text in source videos and your own cards | `tesseract --version` |
| git, curl, unzip, fonts (DejaVu, Noto) | Ubuntu packages | downloads, banner text | `git --version` |
| Python | 3.12 or newer (tested 3.13.7) | all .py scripts | `python3 --version` |

Installed with `apt-get install -y ffmpeg jq tesseract-ocr git curl unzip fonts-dejavu-core fonts-noto-core python3-pip`.
If apt is busy, wait for the other install to finish; never run two at once.

## Runtimes

| Tool | Version tested | Used for | How installed |
|---|---|---|---|
| Node.js | 24.18.0 (22 or newer needed) | HyperFrames, Buffer CLI, PO-token server | NodeSource setup script for Node 22 if missing |
| npm | 12.0.2 | global CLIs | comes with Node |
| Deno | 2.9.7 | yt-dlp solves YouTube's player script with it | official install script into ~/.deno, linked into ~/.local/bin |

## Downloading (free, no logins)

| Tool | Version tested | Used for | How installed |
|---|---|---|---|
| yt-dlp (nightly) | 2026.10.29 nightly | YouTube and TikTok downloads | `pip install --user -U --pre "yt-dlp[default,curl-cffi]"` |
| yt-dlp-ejs | 0.8.0 | YouTube JS challenge solver | pip, same line |
| bgutil-ytdlp-pot-provider | 2.0.2 (plugin and server pinned to the same version) | PO tokens so YouTube serves cloud machines | pip plugin + the server cloned into $TOOLS_DIR/bgutil-ytdlp-pot-provider, `npm ci && npx tsc` |
| wgcf | 2.3.1 | registers an anonymous, free Cloudflare WARP device | release binary into $TOOLS_DIR/warp |
| wireproxy | 1.1.3 | runs WARP as a SOCKS5 proxy on 127.0.0.1:40000 | release binary into $TOOLS_DIR/warp |

Check: `bash scripts/warp_up.sh` prints `warp=on` and `pot-server=on`. The WARP files in $TOOLS_DIR/warp
(wgcf-account.toml, wgcf-profile.conf, wireproxy.conf) hold this agent's own WARP keys: never print, send or commit them
(they are in .gitignore). Update yt-dlp when YouTube breaks: `python3 -m pip install --user -U --pre "yt-dlp[default]" yt-dlp-ejs`.

## Analysis and checks (local, free, CPU)

| Package | Version tested | Used for |
|---|---|---|
| faster-whisper (+ ctranslate2 4.8.3, tokenizers 0.23.3) | 1.2.1 | word-timed transcripts (model `small`, downloaded on first use) |
| onnxruntime | 1.31.0 | CLIP frame descriptions (Xenova/clip-vit-base-patch32) |
| huggingface_hub | 2.2.0 | model downloads into ~/.cache/huggingface |
| mediapipe | 1.1.1 | face, gaze, hand and pose landmarks in qa_video.py, hand_check.py, pose_check.py |
| opencv-python-headless | 4.14 | frames, contact sheets, shot detection |
| scenedetect | 0.7.2 | shot changes |
| librosa, soundfile, pyloudnorm, scipy, numpy, pillow | librosa 1.0.0, pyloudnorm 0.2.0, numpy 2.5.4, pillow 12.3.0 | beats, energy rises, loudness, images |

Installed with one `pip install --user` line in install.sh (with `--break-system-packages` where pip needs it). Face,
hand and object models are downloaded into $AGENT_MODELS by install.sh. Check: `bash selftest.sh`.

## Editing and export

| Tool | Version tested | Used for | How installed |
|---|---|---|---|
| HyperFrames CLI | 0.8.221 | clip cards, titles, word-by-word captions, local render | `npm install -g hyperframes@0.8.221`, then `hyperframes browser ensure` for its Chrome |
| Soundboard | HyperFrames commit 1116077 | 19 sound effects | `bash scripts/soundboard.sh install` |
| scripts/hf_build.py | kit | builds and renders one HyperFrames segment | in the kit |
| scripts/export_final.sh | kit | joins segments, matches loudness, -14 LUFS, chat copy | in the kit |

HyperFrames is not on PATH by default: use `$(npm prefix -g)/bin/hyperframes` or hf_build.py. Never run
`hyperframes auth login` and never give it a HeyGen key: the kit uses it only to render locally, for free.

## Posting (Buffer only, RULE 0)

| Tool | Version tested | Used for | How installed |
|---|---|---|---|
| Buffer CLI (@bufferapp/cli) | 2.0.1 | post, status, metrics | `npm install -g @bufferapp/cli@2.0.1` |

Your key: `BUFFER_API_KEY=` in settings.env (or ~/.config/buffer/env). Check without printing it:
`[ -n "$BUFFER_API_KEY" ] && buffer channels list --output json | jq length`.

## Voice

| Provider | Used for | Setup |
|---|---|---|
| MiniMax or Gemini TTS | voiceover for agents without a face | your own key in settings.env (MINIMAX_API_KEY or GEMINI_API_KEY), AGENT_TTS_PROVIDER and ONE fixed AGENT_TTS_VOICE |

## Avatar route only (`install.sh --with-avatar`)

| Tool | Version tested | Used for | Setup |
|---|---|---|---|
| HeyGen CLI | 0.10.0 | avatar renders, looks, free asset hosting | release binary; sign in with `heygen auth login` (OAuth) so renders bill your plan, never a separate API wallet |

Check credits without printing anything else: `. scripts/env.sh && hg_credits`.

## Reinstall or move to a new machine

```
git clone <this repo> blueprint-kit && cd blueprint-kit
cp settings.example.env settings.env   # fill in
bash install.sh [--with-avatar]
bash selftest.sh
```

install.sh skips what is already installed and pins the versions above (WGCF_VER, WIREPROXY_VER, BGUTIL_VER,
HEYGEN_CLI_VER, HYPERFRAMES_VER, BUFFER_CLI_VER at the top of the file). Change a pin only after testing the new
version on one video.
