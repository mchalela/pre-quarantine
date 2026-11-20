#!/usr/bin/env bash
# Activate the helper-agent rules in THIS folder, which should be a working install.
# Copies agent/CLAUDE.md and agent/settings.json to where Claude Code reads them.
# Run it once after cloning and again after every git pull.
#   tools/install-agent-rules.sh            activate or refresh
#   tools/install-agent-rules.sh --remove   deactivate (for a development clone)
# The rules stop an agent from editing the tools, so never activate them where you develop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKER="$ROOT/.claude/.agent-rules-installed"

case "${1:-}" in
  "")
    if [ ! -f "$ROOT/agent/CLAUDE.md" ] || [ ! -f "$ROOT/agent/settings.json" ]; then
      echo "error: agent/ templates not found in $ROOT" >&2; exit 1
    fi
    mkdir -p "$ROOT/.claude"
    install -m 0644 "$ROOT/agent/CLAUDE.md" "$ROOT/CLAUDE.md"
    install -m 0644 "$ROOT/agent/settings.json" "$ROOT/.claude/settings.json"
    : > "$MARKER"
    echo "agent rules active in $ROOT"
    echo "start a new agent session for them to apply" ;;
  --remove)
    rm -f -- "$ROOT/CLAUDE.md" "$ROOT/.claude/settings.json" "$MARKER"
    rmdir -- "$ROOT/.claude" 2>/dev/null || true
    echo "agent rules removed from $ROOT" ;;
  *)
    echo "usage: tools/install-agent-rules.sh [--remove]" >&2; exit 2 ;;
esac
