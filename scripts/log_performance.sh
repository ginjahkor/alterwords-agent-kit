#!/usr/bin/env bash
# Read-only: pull Buffer's metrics for every post in posts/index.csv (TikTok, Instagram and X) and append them to performance_log.csv.
# Usage: log_performance.sh [--platform tiktok|instagram|x]
set -euo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/env.sh"
ONLY=""; [ "${1:-}" = "--platform" ] && ONLY=${2:-}
LOG=$AGENT_HOME/performance_log.csv
[ -f "$LOG" ] || echo "checked_utc,post_id,slug,views,reactions,comments,shares,avg_watch_sec,eng_rate,metrics_updated,platform,impressions,reach" > "$LOG"
tail -n +2 "$AGENT_POSTS/index.csv" | while IFS=, read -r date pid slug link platform; do
  [ -n "$pid" ] || continue
  platform=${platform:-tiktok}
  [ -z "$ONLY" ] || [ "$ONLY" = "$platform" ] || continue
  buffer posts get --id "$pid" --fields id,metricsUpdatedAt,metrics.type,metrics.value --output json \
  | jq -r --arg now "$(date -u +%FT%TZ)" --arg slug "$slug" --arg plat "$platform" '
      (.metrics // [] | map({(.type): .value}) | add // {}) as $m |
      [$now, .id, $slug, ($m.views // $m.plays), ($m.reactions // $m.likes), $m.comments, ($m.shares // $m.reposts), $m.averageTimeWatched, $m.engagementRate, .metricsUpdatedAt, $plat, $m.impressions, $m.reach] | @csv' \
  | tee -a "$LOG"
done
