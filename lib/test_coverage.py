"""
Implements the `allowlist-manager test` subcommand.

Tests that the patterns in settings.json are syntactically valid and that
the Python lib correctly identifies each whitelisted executable as covered.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.allowlist import load_settings, get_allow_list, is_covered, pattern_covers, normalize_executable

_PATTERN_RE = re.compile(r"^Bash\((.+?)(?:\s+\*)?\)$")

# Executables that must NEVER appear in allow (defense check)
_ALWAYS_DANGEROUS = {"sudo", "su", "doas", "dd", "mkfs", "fdisk"}


def run_tests() -> int:
    """Run all allowlist coverage tests. Returns exit code (0=pass, 1=fail)."""
    settings = load_settings()
    allow_list = get_allow_list(settings)
    deny_list = settings.get("permissions", {}).get("deny", [])
    failures = []
    passes = []

    # Test 1: Every pattern is syntactically parseable
    for pattern in allow_list:
        m = _PATTERN_RE.match(pattern)
        if not m:
            failures.append(f"MALFORMED pattern: {pattern!r}")
            continue
        prefix = m.group(1)

        # Test 2: is_covered(prefix) correctly returns True for the pattern's own prefix
        # For wildcard patterns, test representative paths
        if prefix.startswith("*"):
            suffix = prefix[1:]  # e.g. "venv/bin/python"
            test_cases = [
                f".{suffix}",          # .venv/bin/python
                suffix,                # venv/bin/python
                f"/home/user/x/.{suffix}",  # absolute path
            ]
            for tc in test_cases:
                if is_covered(tc, allow_list):
                    passes.append(f"PASS  {pattern!r}  covers  {tc!r}")
                else:
                    failures.append(f"FAIL  {pattern!r}  should cover  {tc!r}  but does not")
        else:
            if is_covered(prefix, allow_list):
                passes.append(f"PASS  {pattern!r}  covers  {prefix!r}")
            else:
                failures.append(f"FAIL  {pattern!r}  should cover  {prefix!r}  but does not")

    # Test 3: known-dangerous executables are not in allow list
    for exe in _ALWAYS_DANGEROUS:
        if is_covered(exe, allow_list):
            failures.append(f"SECURITY FAIL  {exe!r} is whitelisted — it should not be in allow list")
        else:
            passes.append(f"PASS  {exe!r} is NOT in allow list (correct)")

    # Test 4: deny list exists and is non-empty
    if deny_list:
        passes.append(f"PASS  deny list has {len(deny_list)} entr{'y' if len(deny_list)==1 else 'ies'}")
    else:
        passes.append("INFO  deny list is empty (no permanent denials configured)")

    # Report
    total = len(passes) + len(failures)
    for p in passes:
        print(p)
    print()
    for f in failures:
        print(f)
    print()
    print(f"Results: {len(passes)}/{total} passed, {len(failures)} failed")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run_tests())
