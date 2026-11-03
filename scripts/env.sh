# Shared settings for every bash script in the kit. Source it; it never prints secrets.
# Usage: . "$(dirname "$0")/env.sh"
# Reads KIT_HOME/settings.env (your copy of settings.example.env).

KIT_HOME="${KIT_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export KIT_HOME
export AGENT_SCRIPTS="$KIT_HOME/scripts"
if [ -f "$KIT_HOME/settings.env" ]; then
  set -a; . "$KIT_HOME/settings.env"; set +a
else
  echo "note: $KIT_HOME/settings.env not found, using defaults (copy settings.example.env)" >&2
fi
export AGENT_NAME="${AGENT_NAME:-Agent}" AGENT_SLUG="${AGENT_SLUG:-agent}"
export AGENT_HOME="${AGENT_HOME:-$HOME/agent_studio}"
export AGENT_WORK="${AGENT_WORK:-$AGENT_HOME/work}" AGENT_POSTS="${AGENT_POSTS:-$AGENT_HOME/posts}"
export AGENT_LOOKS="${AGENT_LOOKS:-$AGENT_HOME/looks}" AGENT_MODELS="${AGENT_MODELS:-$AGENT_HOME/models}"
export TOOLS_DIR="${TOOLS_DIR:-$HOME/tools}"
mkdir -p "$AGENT_WORK" "$AGENT_POSTS" "$AGENT_LOOKS" "$AGENT_MODELS" 2>/dev/null

export PATH="$(npm prefix -g 2>/dev/null)/bin:$HOME/.local/bin:$PATH"
# A Buffer key kept outside the kit also works: put BUFFER_API_KEY=... in ~/.config/buffer/env
[ -z "${BUFFER_API_KEY:-}" ] && [ -f ~/.config/buffer/env ] && . ~/.config/buffer/env

# heygen wrapper: bills the plan you signed in to with OAuth, never a separate API wallet
hg() { env -u HEYGEN_API_KEY heygen "$@"; }
# remaining plan credits, nothing else is printed
hg_credits() { hg auth status 2>/dev/null | jq -r '.data.subscription.credits.premium_credits.remaining // "unknown"'; }
