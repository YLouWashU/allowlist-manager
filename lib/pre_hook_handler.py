#!/usr/bin/env python3
"""
PreToolUse hook handler for allowlist-manager.
Detects compound cd+exe commands and auto-approves them, adding the specific
compound pattern to the allowlist so future runs are covered by the allowlist directly.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.parse_sessions import extract_executable
from lib.allowlist import add_exact_pattern
from lib.dangerous import is_dangerous


def _compound_patterns(command: str) -> list:
    """For 'cd PATH && exe ...' commands, return compound Bash(...) patterns to add."""
    patterns = []
    and_parts = [p.strip() for p in command.split('&&')]
    if len(and_parts) < 2:
        return patterns
    first = and_parts[0]
    if not first.startswith('cd '):
        return patterns
    if any(c in first for c in '();\'"$'):
        return patterns
    for part in and_parts[1:]:
        exe = extract_executable(part)
        if exe and not is_dangerous(exe):
            patterns.append(f"Bash({first} && {exe} *)")
    return patterns


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = data.get('tool_input') or data.get('input') or {}
    command = tool_input.get('command', '')

    if not command:
        sys.exit(0)

    patterns = _compound_patterns(command)
    if not patterns:
        sys.exit(0)

    for pattern in patterns:
        add_exact_pattern(pattern)

    # Auto-approve this tool use so the bare-repo security check is bypassed
    print(json.dumps({"decision": "approve"}))


if __name__ == '__main__':
    main()
