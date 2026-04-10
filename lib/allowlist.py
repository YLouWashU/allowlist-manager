import fcntl
import json
import re
from pathlib import Path

SETTINGS_FILE = Path.home() / ".claude" / "settings.json"
LOCK_DIR = Path.home() / ".claude" / "allowlist-manager"

_VENV_RE = re.compile(r"(?:^|.*/)([^/]*venv/bin/(.+))$")


def normalize_executable(executable: str) -> str:
    """If executable is under a venv/bin/, return *venv/bin/<basename> wildcard form."""
    m = _VENV_RE.match(executable)
    if m:
        return f"*venv/bin/{m.group(2)}"
    return executable


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    with open(SETTINGS_FILE) as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


def get_allow_list(settings: dict) -> list:
    return settings.get("permissions", {}).get("allow", [])


def pattern_covers(pattern: str, executable: str) -> bool:
    """Return True if a Bash(prefix *) pattern covers the given executable.
    Supports glob-style * at the start of prefix (e.g. *venv/bin/python).
    """
    m = re.match(r"^Bash\((.+?)(?:\s+\*)?\)$", pattern)
    if not m:
        return False
    prefix = m.group(1)
    if prefix.startswith("*"):
        suffix = prefix[1:]
        return executable.endswith(suffix)
    return executable == prefix or executable.startswith(prefix + "/")


def is_covered(executable: str, allow_list: list) -> bool:
    norm = normalize_executable(executable)
    return any(pattern_covers(p, executable) or pattern_covers(p, norm) for p in allow_list)


def _with_lock(fn):
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = LOCK_DIR / "settings.lock"
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            fn()
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


def add_pattern(executable: str) -> None:
    """Add Bash(executable *) to permissions.allow if not already covered.
    Venv-path executables are automatically expanded to wildcard form.
    """
    norm = normalize_executable(executable)

    def _do():
        settings = load_settings()
        allow = settings.setdefault("permissions", {}).setdefault("allow", [])
        if not is_covered(norm, allow):
            allow.append(f"Bash({norm} *)")
            save_settings(settings)
    _with_lock(_do)


def add_deny_pattern(executable: str) -> None:
    """Add Bash(executable *) to permissions.deny."""
    def _do():
        settings = load_settings()
        deny = settings.setdefault("permissions", {}).setdefault("deny", [])
        pattern = f"Bash({executable} *)"
        if pattern not in deny:
            deny.append(pattern)
            save_settings(settings)
    _with_lock(_do)
