# Decisions Log — allowlist-manager implementation

## D1: fcntl locking in dangerous.py queue operations

**Decision:** Added `fcntl.flock` to `append_to_queue` and `write_queue` for concurrent write safety.

**Why:** The spec called for locking in `allowlist.py` (settings.json writes) but didn't explicitly mention locking in `dangerous.py`. The hook fires on every Bash command and could overlap with itself in rapid-fire sessions, corrupting the JSONL queue. Applied the same pattern for consistency.

**Trade-off:** Negligible overhead. No downside.

---

## D2: `hook.sh` uses `set -euo pipefail` but wraps with `|| true`

**Decision:** The hook script uses strict mode for its own logic but the final python3 call has `|| true` appended.

**Why:** The hook must never cause Claude Code to error or block. If `hook_handler.py` fails for any reason (malformed JSON, filesystem error, Python bug), it silently exits 0. The `2>/dev/null` suppresses stderr noise. This matches the plan spec exactly.

---

## D3: SKILL.md uses `$HOME` not `~` in Python code blocks

**Decision:** All `sys.path.insert` calls in SKILL.md use `$HOME/.claude/skills/allowlist-manager` (shell-expanded string), not `~`.

**Why:** The Python code blocks in SKILL.md are run via `python3 -c "..."` inside bash. `~` is not expanded inside Python string literals, but `$HOME` is expanded by the shell before Python sees it.

---

## D4: `tests/__init__.py` kept empty

**Decision:** Did not add `__init__.py` content for test discovery.

**Why:** Python `unittest discover` works without it. The empty file just marks the directory as a package for explicit imports (`python3 -m unittest tests.test_dangerous`).

---

## D5: No `tests/test_hook_handler.py` written

**Decision:** Skipped unit tests for `hook_handler.py` as planned (Task 4 note: "No unit tests — thin I/O entry point; integration tested via hook.sh").

**Why:** `hook_handler.py` is a ~40-line I/O adapter. Its logic is entirely covered by tests of `split_command`, `extract_executable`, `is_covered`, `is_dangerous`, `append_to_queue`, and `add_pattern` — all of which have unit tests. The smoke test in Task 5 confirmed end-to-end wiring.
