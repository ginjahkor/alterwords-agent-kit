#!/usr/bin/env bash
# Make sure the YouTube helpers are running:
#  1) Cloudflare WARP tunnel (wireproxy, free, anonymous WARP device, no account login) as SOCKS5 on 127.0.0.1:40000.
#     YouTube blocks this VM's datacenter IP ("Sign in to confirm you're not a bot").
#     Some WARP exit IPs are blocked too, so --restart reconnects for a different exit IP.
#  2) bgutil PO-token server on 127.0.0.1:4416 (yt-dlp plugin bgutil-ytdlp-pot-provider uses it automatically).
# No cookies, no logins (RULE 0).
# Usage: warp_up.sh            -> start if needed, print exit IP
#        warp_up.sh --restart  -> reconnect the tunnel (new exit IP most of the time)
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
W=$TOOLS_DIR/warp
B=$TOOLS_DIR/bgutil-ytdlp-pot-provider/server
if [ "${1:-}" = "--restart" ]; then pkill -x wireproxy; sleep 1; fi
if ! pgrep -x wireproxy >/dev/null; then
  cd "$W" && setsid nohup ./wireproxy -c wireproxy.conf </dev/null > wireproxy.log 2>&1 &
  sleep 5
fi
if ! curl -s --max-time 3 http://127.0.0.1:4416/ping >/dev/null 2>&1; then
  cd "$B" && setsid nohup node build/main.js </dev/null > $TOOLS_DIR/bgutil_server.log 2>&1 &
  sleep 3
fi
TRACE=$(curl -s --max-time 15 -x socks5h://127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace)
echo "$TRACE" | grep -E "^(ip|warp)=" || { echo "WARP tunnel not answering" >&2; exit 1; }
curl -s --max-time 3 http://127.0.0.1:4416/ping >/dev/null && echo "pot-server=on" || echo "pot-server=off"
