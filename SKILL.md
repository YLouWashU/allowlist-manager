---
name: allowlist-manager
description: "Manage ~/.claude/settings.json permissions.allow list. Reduces repeated permission prompts by auto-capturing approved commands (via hook) and retroactively adding historical patterns (via init). Subcommands: init, init-dry-run, enable-auto, disable-auto, add-skipped-commands, test."
---

You are the allowlist-manager skill. Parse the first argument...

You are the allowlist-manager skill. Parse the first argument to determine which subcommand to run.

SCRIPT_DIR: ~/.claude/skills/allowlist-manager
LIB_DIR: ~/.claude/skills/allowlist-manager/lib
SETTINGS: ~/.claude/settings.json
QUEUE: ~/.claude/allowlist-manager/skipped.jsonl

## Venv path expansion (applies to init and add-skipped-commands)

Whenever an executable is a venv-path command (its path contains `venv/bin/`), **always expand
it to a wildcard pattern** so it covers any venv anywhere:

| Raw executable                                | Pattern to add            |
|-----------------------------------------------|---------------------------|
| `.venv/bin/python`                            | `Bash(*venv/bin/python *)` |
| `venv/bin/pip`                                | `Bash(*venv/bin/pip *)`    |
| `/home/louy/Code/proj/.venv/bin/pytest`       | `Bash(*venv/bin/pytest *)` |

The `add_pattern()` function in `lib/allowlist.py` does this automatically — just pass the raw
executable and it will store the expanded wildcard form.

## No-arg: show help

Print this help text:

```
allowlist-manager — manage your Claude Code permissions.allow list

Subcommands:
  init [--since DATE] [--until DATE]
      Scan session history over a time range. Show safe-gap patterns grouped
      by category. Ask for confirmation per group before writing to settings.json.
      Venv-path commands are automatically expanded to *venv/bin/<exe> wildcards.

  init-dry-run [--since DATE] [--until DATE]
      Same scan, read-only. Print a table of all executables with coverage status.

  enable-auto
      Install the PostToolUse hook so new approved commands are captured automatically.

  disable-auto
      Remove the PostToolUse hook.

  add-skipped-commands
      Review dangerous commands queued by the hook. Approve or deny each one.
      Venv-path commands are automatically expanded to *venv/bin/<exe> wildcards.

  test
      Validate that every pattern in settings.json is syntactically correct and
      that the lib correctly identifies each whitelisted executable as covered.
      Also checks that known-dangerous executables (sudo, dd, etc.) are NOT allowed.

Date formats: "2 weeks ago", "last month", 2026-03-01
```

## Subcommand: init

Parse --since and --until from the arguments. If neither is provided, ask the user:
> "What time range should I scan? (e.g. 'last 2 weeks', 'since 2026-03-01', 'all time')"

Convert natural language dates to datetime objects using Python's datetime.
For "all time", pass since=None, until=None.

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/skills/allowlist-manager')
from lib.parse_sessions import parse_sessions, classify_executables
from lib.allowlist import load_settings, get_allow_list
import json
from datetime import datetime, timezone

since = None  # replace with parsed datetime if provided
until = None  # replace with parsed datetime if provided

counts = parse_sessions(since=since, until=until)
settings = load_settings()
allow_list = get_allow_list(settings)
classified = classify_executables(counts, allow_list)

print(json.dumps(classified, indent=2))
"
```

Present the safe_gap entries grouped by category as a table. For venv-path executables,
show the expanded wildcard pattern in the Pattern column:
```
Category          Executable                Count   Pattern
──────────────────────────────────────────────────────────────
package_manager   uv                        12      Bash(uv *)
runtime           .venv/bin/python          8       Bash(*venv/bin/python *)
other             agent-browser             5       Bash(agent-browser *)
```

For each category group, ask: "Add these N patterns? [y/n/select]"
- y → add all in group
- n → skip group
- select → list patterns one by one for individual approval

After all confirmations, write approved patterns using add_pattern() — venv expansion is
automatic inside add_pattern():
```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/skills/allowlist-manager')
from lib.allowlist import add_pattern
add_pattern('EXECUTABLE_HERE')
"
```

Also show dangerous_gap entries as a warning (do NOT add them):
```
⚠ Dangerous commands found (not added — use add-skipped-commands to review):
  sudo (3 occurrences), dd (1 occurrence)
```

## Subcommand: init-dry-run

Same as init but never write anything. Print the full classification table:
```
Status          Category          Executable                Count
────────────────────────────────────────────────────────────────
✓ covered       vcs               git                       47
✓ covered       runtime           python3                   31
+ safe gap      package_manager   uv                        12
+ safe gap      runtime           .venv/bin/python          8
⚠ dangerous     escalation        sudo                      3
```

End with a summary:
```
Summary: 12 covered, 8 safe gaps (would be added by init), 2 dangerous (review manually)
```

## Subcommand: enable-auto

Read ~/.claude/settings.json. Add the PostToolUse hook entry if not already present:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "~/.claude/skills/allowlist-manager/hook.sh"}]
      }
    ]
  }
}
```

Merge carefully — preserve any existing hooks. Use Python to read and write:
```bash
python3 -c "
import json, sys
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}

hook_entry = {
    'matcher': 'Bash',
    'hooks': [{'type': 'command', 'command': str(Path.home() / '.claude/skills/allowlist-manager/hook.sh')}]
}

hooks = settings.setdefault('hooks', {})
post = hooks.setdefault('PostToolUse', [])

# Check not already installed
already = any(
    any(h.get('command', '').endswith('allowlist-manager/hook.sh') for h in e.get('hooks', []))
    for e in post
)
if not already:
    post.append(hook_entry)
    settings_path.write_text(json.dumps(settings, indent=2) + '\n')
    print('Hook installed.')
else:
    print('Hook already installed.')
"
```

Confirm to user: "Auto-capture enabled. Every new Bash command will be checked and added to your allow list."

## Subcommand: disable-auto

Remove the allowlist-manager hook entry from settings.json:

```bash
python3 -c "
import json
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
if not settings_path.exists():
    print('settings.json not found.')
    exit()

settings = json.loads(settings_path.read_text())
post = settings.get('hooks', {}).get('PostToolUse', [])
filtered = [
    e for e in post
    if not any(h.get('command', '').endswith('allowlist-manager/hook.sh') for h in e.get('hooks', []))
]
settings['hooks']['PostToolUse'] = filtered
settings_path.write_text(json.dumps(settings, indent=2) + '\n')
print('Hook removed.')
"
```

Confirm: "Auto-capture disabled."

## Subcommand: add-skipped-commands

Read the queue:
```bash
python3 -c "
import sys, json
sys.path.insert(0, '$HOME/.claude/skills/allowlist-manager')
from lib.dangerous import read_queue
entries = read_queue()
print(json.dumps(entries, indent=2))
"
```

If queue is empty, say: "No skipped commands to review."

Otherwise, group entries by executable. For each group, present:
```
Executable: sudo (3 occurrences)
Sample commands:
  - sudo apt install ripgrep
  - sudo systemctl restart nginx

Options:
  A) Allow with broad pattern: Bash(sudo *)
  B) Allow specific pattern (I'll propose one based on the commands)
  S) Skip — leave in queue
  D) Deny permanently — add to permissions.deny
```

After user choice:
- A → run: `python3 -c "import sys; sys.path.insert(0,'$HOME/.claude/skills/allowlist-manager'); from lib.allowlist import add_pattern; add_pattern('EXECUTABLE')"`
  Note: if EXECUTABLE is a venv path (e.g. `.venv/bin/mylib`), add_pattern() automatically
  expands it to `Bash(*venv/bin/mylib *)`.
- B → analyse the sample commands, propose the tightest pattern that covers them, confirm with user, then add
- S → leave entry in queue (don't remove)
- D → run: `python3 -c "import sys; sys.path.insert(0,'$HOME/.claude/skills/allowlist-manager'); from lib.allowlist import add_deny_pattern; add_deny_pattern('EXECUTABLE')"`

After processing all non-skipped groups, remove their entries from the queue:
```bash
python3 -c "
import sys, json
sys.path.insert(0, '$HOME/.claude/skills/allowlist-manager')
from lib.dangerous import read_queue, write_queue
entries = read_queue()
# Keep only skipped executables (replace SET_OF_SKIPPED with actual set)
keep_exes = SET_OF_SKIPPED_EXECUTABLES_HERE
remaining = [e for e in entries if e['executable'] in keep_exes]
write_queue(remaining)
print(f'Queue updated: {len(remaining)} entries remaining.')
"
```

## Subcommand: test

Run the coverage test script:
```bash
python3 $HOME/.claude/skills/allowlist-manager/lib/test_coverage.py
```

The script validates:
1. Every `Bash(...)` pattern in settings.json is syntactically parseable
2. The lib correctly identifies each whitelisted executable as covered (including wildcard
   patterns like `Bash(*venv/bin/python *)` covering `.venv/bin/python`, `venv/bin/python`,
   and absolute paths)
3. Known-dangerous executables (sudo, dd, su, doas, mkfs, fdisk) are NOT in the allow list
4. The deny list exists

Show the full output to the user. Exit code 0 = all pass, 1 = failures found.

Example output:
```
PASS  'Bash(git *)' covers 'git'
PASS  'Bash(*venv/bin/python *)' covers '.venv/bin/python'
PASS  'Bash(*venv/bin/python *)' covers 'venv/bin/python'
...
PASS  'sudo' is NOT in allow list (correct)
PASS  deny list has 1 entry

Results: 111/111 passed, 0 failed
```
