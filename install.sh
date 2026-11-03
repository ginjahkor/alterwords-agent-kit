#!/usr/bin/env bash
# install.sh - set up everything the kit needs on a fresh Ubuntu/Debian machine, then run the self-test.
# Usage: bash install.sh [--with-avatar] [--skip-selftest]
#   --with-avatar   also install the HeyGen CLI (only for agents the owner gave an avatar)
# Safe to run again: every step checks what is already there.
# It installs tools only. It never asks for, prints or stores a key. Each agent adds its own keys afterwards
# (settings.env, ~/.config/buffer/env, `heygen auth login`).
set -uo pipefail
KIT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; export KIT_HOME
WITH_AVATAR=0; SELFTEST=1
for a in "$@"; do case "$a" in --with-avatar) WITH_AVATAR=1;; --skip-selftest) SELFTEST=0;; esac; done

# Pinned versions (tested together). Bump them on purpose, then rerun selftest.sh.
WGCF_VER=2.3.1; WIREPROXY_VER=1.1.3; BGUTIL_VER=2.0.2; HEYGEN_CLI_VER=0.10.0
HYPERFRAMES_VER=0.8.221; BUFFER_CLI_VER=2.0.1

step() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; FAILS=$((FAILS+1)); }
FAILS=0
SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO=sudo
ARCH=$(uname -m); case "$ARCH" in x86_64) GOARCH=amd64;; aarch64|arm64) GOARCH=arm64;; *) GOARCH=$ARCH;; esac

[ -f "$KIT_HOME/settings.env" ] || { cp "$KIT_HOME/settings.example.env" "$KIT_HOME/settings.env"; echo "Created settings.env from settings.example.env: fill it in for your agent."; }
. "$KIT_HOME/scripts/env.sh"
mkdir -p "$TOOLS_DIR/warp" "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$HOME/.deno/bin:$PATH"

step "System packages (ffmpeg, jq, tesseract, git, fonts)"
NEED=""
for p in ffmpeg jq tesseract git curl unzip; do command -v $p >/dev/null || NEED="$NEED $p"; done
[ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ] || NEED="$NEED fonts-dejavu-core"
NEED=${NEED/tesseract/tesseract-ocr}
if [ -n "$NEED" ]; then $SUDO apt-get update -qq && $SUDO apt-get install -y -qq $NEED python3-pip || warn "apt could not install:$NEED"; fi
ffmpeg -hide_banner -version | head -1

step "Node.js (HyperFrames, Buffer CLI, PO-token server need Node 22 or newer)"
NODE_MAJOR=$(node -v 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/'); NODE_MAJOR=${NODE_MAJOR:-0}
if [ "$NODE_MAJOR" -lt 22 ]; then
  warn "Node $NODE_MAJOR found. Install Node 22+ (for example from nodesource or nvm), then run install.sh again."
else node -v; fi

step "Deno (yt-dlp uses it to solve YouTube's player script)"
command -v deno >/dev/null || curl -fsSL https://deno.land/install.sh | sh -s -- -y >/dev/null || warn "deno install failed"
deno --version 2>/dev/null | head -1

step "Python packages"
PIPF="--user -q"; python3 -m pip install --help 2>/dev/null | grep -q break-system-packages && PIPF="$PIPF --break-system-packages"
python3 -m pip install $PIPF -U --pre "yt-dlp[default,curl-cffi]" yt-dlp-ejs "bgutil-ytdlp-pot-provider==$BGUTIL_VER" || warn "yt-dlp install failed"
python3 -m pip install $PIPF numpy opencv-python-headless mediapipe librosa soundfile pyloudnorm "scenedetect[opencv-headless]" \
  onnxruntime tokenizers huggingface_hub pillow faster-whisper || warn "some Python packages failed"
yt-dlp --version

step "HyperFrames + Buffer CLI (npm, global)"
NPM_BIN="$(npm prefix -g 2>/dev/null)/bin"
if [ ! -w "$(npm prefix -g 2>/dev/null)" ]; then npm config set prefix "$HOME/.npm-global"; NPM_BIN="$HOME/.npm-global/bin"; fi
export PATH="$NPM_BIN:$PATH"
npm install -g -s "hyperframes@$HYPERFRAMES_VER" "@bufferapp/cli@$BUFFER_CLI_VER" || warn "npm global install failed"
hyperframes --version 2>/dev/null | head -1

step "bgutil PO-token server (YouTube proof-of-origin tokens, no login)"
BG="$TOOLS_DIR/bgutil-ytdlp-pot-provider"
if [ ! -f "$BG/server/build/main.js" ]; then
  rm -rf "$BG"
  git -c advice.detachedHead=false clone -q --depth 1 --branch "$BGUTIL_VER" https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git "$BG" \
    && (cd "$BG/server" && npm ci -s && npx tsc) || warn "PO-token server build failed"
fi
[ -f "$BG/server/build/main.js" ] && echo "PO-token server built"

step "Cloudflare WARP tunnel (free, anonymous; YouTube blocks most datacenter IPs)"
cd "$TOOLS_DIR/warp"
[ -x wgcf ] || { curl -fsSL -o wgcf "https://github.com/ViRb3/wgcf/releases/download/v$WGCF_VER/wgcf_${WGCF_VER}_linux_$GOARCH" && chmod +x wgcf; } || warn "wgcf download failed"
[ -x wireproxy ] || { curl -fsSL "https://github.com/windtf/wireproxy/releases/download/v$WIREPROXY_VER/wireproxy_linux_$GOARCH.tar.gz" | tar xz wireproxy; } || warn "wireproxy download failed"
if [ ! -f wireproxy.conf ]; then
  # Registers a NEW anonymous WARP device for THIS agent. The generated files hold this agent's own WireGuard key:
  # they stay on this machine (chmod 600) and must never be copied into the repo.
  ( [ -f wgcf-account.toml ] || ./wgcf register --accept-tos >/dev/null ) && ./wgcf generate >/dev/null \
    && { cat wgcf-profile.conf; printf '\n[Socks5]\nBindAddress = 127.0.0.1:40000\n'; } > wireproxy.conf \
    && chmod 600 wgcf-account.toml wgcf-profile.conf wireproxy.conf || warn "WARP registration failed"
fi
cd "$KIT_HOME"
bash scripts/warp_up.sh || warn "WARP tunnel did not answer (try: bash scripts/warp_up.sh --restart)"

step "Vision models -> $AGENT_MODELS"
dl() { [ -s "$AGENT_MODELS/$1" ] || curl -fsSL -o "$AGENT_MODELS/$1" "$2" || { rm -f "$AGENT_MODELS/$1"; warn "model $1 failed"; }; }
Z=https://github.com/opencv/opencv_zoo/raw/main/models
MP=https://storage.googleapis.com/mediapipe-models
dl yunet.onnx "$Z/face_detection_yunet/face_detection_yunet_2023mar.onnx"
dl sface.onnx "$Z/face_recognition_sface/face_recognition_sface_2021dec.onnx"
dl yolox_s.onnx "$Z/object_detection_yolox/object_detection_yolox_2022nov.onnx"
dl face_landmarker.task "$MP/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
dl hand_landmarker.task "$MP/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
ls -la "$AGENT_MODELS" | tail -n +2

if [ $WITH_AVATAR = 1 ]; then
  step "HeyGen CLI (avatar route)"
  command -v heygen >/dev/null || curl -fsSL "https://github.com/heygen-com/heygen-cli/releases/download/v$HEYGEN_CLI_VER/heygen_v${HEYGEN_CLI_VER}_linux_$GOARCH.tar.gz" \
    | tar xz -C "$HOME/.local/bin" heygen || warn "HeyGen CLI install failed"
  heygen --version 2>/dev/null | head -1
  echo "Next: run 'heygen auth login' yourself (OAuth, bills your plan). Never paste a key into the repo."
fi

step "Soundboard (19 sound effects from HyperFrames, pinned commit)"
bash "$KIT_HOME/scripts/soundboard.sh" install || warn "soundboard download failed (run scripts/soundboard.sh install later)"
bash "$KIT_HOME/templates/make_test_assets.sh" || warn "template test assets not made"

chmod +x "$KIT_HOME"/scripts/*.sh "$KIT_HOME"/scripts/*.py "$KIT_HOME"/*.sh 2>/dev/null
step "Install finished with $FAILS warning(s)"
if [ $SELFTEST = 1 ]; then bash "$KIT_HOME/selftest.sh"; fi
