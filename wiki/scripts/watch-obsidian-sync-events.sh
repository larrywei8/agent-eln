#!/usr/bin/env bash
set -euo pipefail

# Default ROOT resolves to the repo root (agent-eln/), which contains wiki/.
# Pass an explicit path as arg 1 if your wiki lives elsewhere.
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-${AGENT_ELN_WIKI_ROOT:-$(cd "$_HERE/../.." && pwd)}}"
OUT_DIR="$ROOT/outputs/obsidian-sync"
EVENT_LOG="$OUT_DIR/events.jsonl"
SUMMARY_LOG="$OUT_DIR/events.md"

mkdir -p "$OUT_DIR"
touch "$EVENT_LOG" "$SUMMARY_LOG"

echo "# Obsidian/Zo Knowledge Sync Events" > "$SUMMARY_LOG"
echo >> "$SUMMARY_LOG"
echo "Watcher started: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SUMMARY_LOG"
echo >> "$SUMMARY_LOG"

inotifywait -m -r \
  -e close_write,create,delete,moved_to,moved_from \
  --exclude '(^|/)(\.stversions|\.stfolder|\.syncthing.*|\.obsidian)(/|$)|(^|/)outputs/obsidian-sync/events\.(jsonl|md)$|(~$|\.swp$|\.tmp$)' \
  --timefmt '%Y-%m-%dT%H:%M:%SZ' \
  --format '%T	%e	%w%f' \
  "$ROOT" | while IFS=$'\t' read -r ts event path; do
    rel="${path#$ROOT/}"
    printf '{"timestamp":"%s","event":"%s","path":"%s"}\n' \
      "$ts" \
      "$(printf '%s' "$event" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])')" \
      "$(printf '%s' "$rel" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read())[1:-1])')" \
      >> "$EVENT_LOG"
    printf -- '- `%s` `%s` `%s`\n' "$ts" "$event" "$rel" >> "$SUMMARY_LOG"
  done
