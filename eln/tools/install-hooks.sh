#!/usr/bin/env bash
# One-time install of the git hook. If this isn't a git repo yet, run git init first.
# Usage: bash tools/install-hooks.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -d .git ]; then
  echo "This directory is not a git repo yet; running git init …"
  git init -q
fi
cp tools/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "✅ pre-commit hook installed: index + validate run automatically before each commit; failed validation blocks the commit."
