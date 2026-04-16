#!/usr/bin/env bash
# PreToolUse hook for allowlist-manager.
# Detects compound cd+exe commands, adds the compound pattern to the allowlist,
# and auto-approves the tool use to bypass the bare-repo security check.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "$SCRIPT_DIR/lib/pre_hook_handler.py" 2>/dev/null || true
