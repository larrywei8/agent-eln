#!/usr/bin/env bash
set -u -o pipefail

# Default ROOT resolves to the repo root (agent-eln/), which contains wiki/.
# Override with --root or AGENT_ELN_WIKI_ROOT if your wiki lives elsewhere.
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${AGENT_ELN_WIKI_ROOT:-$(cd "$_HERE/../.." && pwd)}"
SKILL="${LLM_WIKI_ANYGEN:-/home/workspace/Skills/llm-wiki-anygen}"
BACKUP_ROOT="${AGENT_ELN_OBSIDIAN_BACKUP_ROOT:-$ROOT/.obsidian-sync-backups}"
REPORT_ROOT="$ROOT/outputs/obsidian-sync"
APPLY=0
RUN_LINT=1

usage() {
  cat <<USAGE
sync-obsidian-back.sh — prepare Obsidian edits for the wiki

Usage:
  bash wiki/scripts/sync-obsidian-back.sh [--apply] [--root <path-with-wiki/>] [--no-lint]

Default mode is dry-run: it reports wikilinks that would be converted and does not edit files.
Use --apply to:
  1. Back up the current wiki tree under \$ROOT/.obsidian-sync-backups/ (override with AGENT_ELN_OBSIDIAN_BACKUP_ROOT)
  2. Convert Obsidian [[wikilinks]] under \$ROOT/wiki/ to standard Markdown links
  3. Run the llm-wiki-anygen wiki linter
  4. Write logs under \$ROOT/outputs/obsidian-sync/
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --root)
      ROOT="${2:-}"
      shift 2
      ;;
    --no-lint)
      RUN_LINT=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

MIGRATE="$SKILL/scripts/migrate_wikilinks.py"
LINT="$SKILL/scripts/lint_wiki.py"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
REPORT_DIR="$REPORT_ROOT/$STAMP"
mkdir -p "$REPORT_DIR"

if [[ ! -d "$ROOT/wiki" ]]; then
  echo "ERROR: wiki directory not found at $ROOT/wiki" >&2
  exit 1
fi
if [[ ! -f "$MIGRATE" ]]; then
  echo "ERROR: migrate script not found at $MIGRATE" >&2
  exit 1
fi
if [[ ! -f "$LINT" ]]; then
  echo "ERROR: lint script not found at $LINT" >&2
  exit 1
fi

MODE="dry-run"
if [[ "$APPLY" -eq 1 ]]; then
  MODE="apply"
fi

SUMMARY="$REPORT_DIR/summary.md"
{
  echo "# Obsidian Sync Back Report"
  echo
  echo "- Timestamp UTC: $STAMP"
  echo "- Mode: $MODE"
  echo "- Wiki root: $ROOT"
  echo
} > "$SUMMARY"

echo "Mode: $MODE"
echo "Report: $REPORT_DIR"

if [[ "$APPLY" -eq 1 ]]; then
  BACKUP_DIR="$BACKUP_ROOT/knowledge-$STAMP"
  mkdir -p "$BACKUP_ROOT"
  echo "Creating backup: $BACKUP_DIR"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.git/' \
      --exclude '.graph-cache/' \
      --exclude 'outputs/obsidian-sync/' \
      "$ROOT/" "$BACKUP_DIR/"
  else
    mkdir -p "$BACKUP_DIR"
    tar -C "$ROOT" \
      --exclude './.git' \
      --exclude './.graph-cache' \
      --exclude './outputs/obsidian-sync' \
      -cf - . | tar -C "$BACKUP_DIR" -xf -
  fi
  echo "- Backup: $BACKUP_DIR" >> "$SUMMARY"
else
  echo "Dry-run only: no backup created and no files edited."
  echo "- Backup: none; dry-run mode" >> "$SUMMARY"
fi

MIGRATE_LOG="$REPORT_DIR/migrate.log"
echo "Running wikilink migration..."
if [[ "$APPLY" -eq 1 ]]; then
  python3 "$MIGRATE" "$ROOT" --apply > "$MIGRATE_LOG" 2>&1
else
  python3 "$MIGRATE" "$ROOT" > "$MIGRATE_LOG" 2>&1
fi
MIGRATE_STATUS=$?
cat "$MIGRATE_LOG"
{
  echo
  echo "## Wikilink Migration"
  echo
  echo "- Exit code: $MIGRATE_STATUS"
  echo "- Log: $MIGRATE_LOG"
} >> "$SUMMARY"

LINT_STATUS="skipped"
if [[ "$RUN_LINT" -eq 1 && "$APPLY" -eq 1 ]]; then
  LINT_LOG="$REPORT_DIR/lint.log"
  echo "Running wiki linter..."
  python3 "$LINT" "$ROOT" > "$LINT_LOG" 2>&1
  LINT_STATUS=$?
  cat "$LINT_LOG"
  {
    echo
    echo "## Wiki Lint"
    echo
    echo "- Exit code: $LINT_STATUS"
    echo "- Log: $LINT_LOG"
  } >> "$SUMMARY"
elif [[ "$RUN_LINT" -eq 1 ]]; then
  echo "Skipping lint in dry-run mode because lint refreshes graph artifacts. Re-run with --apply to lint."
  {
    echo
    echo "## Wiki Lint"
    echo
    echo "- Exit code: skipped"
    echo "- Reason: dry-run mode avoids graph artifact writes"
  } >> "$SUMMARY"
else
  echo "Lint skipped by --no-lint."
fi

if git -C /home/workspace rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_STATUS_LOG="$REPORT_DIR/git-status.log"
  git -C /home/workspace status --short > "$GIT_STATUS_LOG" 2>&1 || true
  {
    echo
    echo "## Git Status"
    echo
    echo "- Log: $GIT_STATUS_LOG"
  } >> "$SUMMARY"
fi

cat <<DONE

Finished.
Summary: $SUMMARY
Migration exit code: $MIGRATE_STATUS
Lint exit code: $LINT_STATUS
DONE

if [[ "$MIGRATE_STATUS" -ne 0 ]]; then
  exit "$MIGRATE_STATUS"
fi
if [[ "$LINT_STATUS" != "skipped" && "$LINT_STATUS" -ne 0 ]]; then
  exit "$LINT_STATUS"
fi
exit 0
