#!/usr/bin/env bash
# PostToolUse hook for allowlist-manager.
# Receives Claude Code tool JSON on stdin, delegates to hook_handler.py.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pass stdin directly to hook_handler.py; suppress all errors (hook must not break Claude)
python3 "$SCRIPT_DIR/lib/hook_handler.py" 2>/dev/null || true
