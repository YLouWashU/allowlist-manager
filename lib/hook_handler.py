#!/usr/bin/env python3
"""
Entry point called by hook.sh. Reads Claude Code PostToolUse JSON from stdin,
extracts the Bash command, and either adds it to the allow list or queues it.
"""
import json
import sys
from pathlib import Path

# Allow running as script from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.parse_sessions import split_command, extract_executable
from lib.allowlist import load_settings, get_allow_list, is_covered, add_pattern
from lib.dangerous import is_dangerous, append_to_queue


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # Claude Code PostToolUse hook format:
    # {"tool_name": "Bash", "tool_input": {"command": "..."}, "tool_response": {...}}
    tool_input = data.get('tool_input') or data.get('input') or {}
    command = tool_input.get('command', '')
    session = data.get('session_id', '')

    if not command:
        sys.exit(0)

    settings = load_settings()
    allow_list = get_allow_list(settings)

    for sub in split_command(command):
        exe = extract_executable(sub)
        if not exe:
            continue
        if is_covered(exe, allow_list):
            continue
        if is_dangerous(exe):
            append_to_queue(command, exe, session)
        else:
            add_pattern(exe)
            # Reload allow list so subsequent subs in same command see the update
            settings = load_settings()
            allow_list = get_allow_list(settings)


if __name__ == '__main__':
    main()
