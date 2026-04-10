# allowlist-manager

Auto-capture and manage Claude Code `permissions.allow` patterns from session history.

## Install

```bash
npx skills add YLouWashU/allowlist-manager -g -y
```

## Commands

| Subcommand | Description |
|------------|-------------|
| `init [--since DATE]` | Scan session history, add safe commands to allowlist |
| `init-dry-run` | Preview what `init` would add (read-only) |
| `enable-auto` | Install PostToolUse hook for live capture |
| `disable-auto` | Remove the hook |
| `add-skipped-commands` | Review queued dangerous commands |
| `test` | Validate allowlist coverage (111/111 patterns tested) |

## Features

- **Venv wildcards** — `venv/bin/python` auto-expands to `Bash(*venv/bin/python *)`, covering any venv anywhere
- **Concurrent safe** — fcntl-based locking for overlapping hook invocations
- **Dangerous filtering** — `sudo`, `dd`, `rm -rf`, etc. are queued for manual review, never auto-added

## How it works

The `init` command parses `~/.claude/projects/**/*.jsonl` session files, extracts executables, and classifies them:

- **covered** — already in allowlist, skip
- **safe gap** — not covered, not dangerous → prompt to add
- **dangerous gap** — not covered, risky → queue for review

The `enable-auto` hook runs on every Bash command and auto-adds safe executables, queue dangerous ones.