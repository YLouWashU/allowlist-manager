import json
import re
from datetime import datetime, timezone
from pathlib import Path


CATEGORIES = {
    'package_manager': {'pip', 'pip3', 'npm', 'npx', 'yarn', 'pnpm', 'cargo', 'gem', 'brew', 'uv'},
    'runtime': {'python', 'python3', 'python3.12', 'node', 'ruby', 'perl', 'php', 'java', 'deno', 'bun'},
    'vcs': {'git', 'gh', 'hg', 'svn'},
    'shell': {'bash', 'sh', 'zsh', 'fish'},
    'system': {'systemctl', 'journalctl', 'loginctl', 'crontab'},
    'network': {'curl', 'wget', 'ssh', 'scp', 'rsync'},
    'media': {'ffmpeg', 'ffprobe', 'convert', 'magick'},
    'build': {'make', 'cmake', 'ninja', 'tsc', 'webpack', 'vite'},
}


def iter_session_files(since=None, until=None):
    """Yield all .jsonl session files, optionally filtered by mtime."""
    projects_dir = Path.home() / '.claude' / 'projects'
    if not projects_dir.exists():
        return
    for p in projects_dir.rglob('*.jsonl'):
        if since or until:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if since and mtime < since:
                continue
            if until and mtime > until:
                continue
        yield p


def split_command(command: str) -> list:
    """Split a compound shell command into individual sub-commands."""
    parts = re.split(r'&&|\|\||;|\|', command)
    return [p.strip() for p in parts if p.strip()]


def extract_executable(sub_command: str) -> str | None:
    """Extract the executable (first meaningful token) from a sub-command."""
    sub_command = sub_command.strip()
    if not sub_command or sub_command.startswith('#'):
        return None
    tokens = sub_command.split()
    for token in tokens:
        if re.match(r'^[A-Z_][A-Z0-9_]*=', token):
            continue
        return token
    return None


def categorize(executable: str) -> str:
    """Return the category name for an executable."""
    name = Path(executable).name
    for cat, names in CATEGORIES.items():
        if name in names:
            return cat
    if '/' in executable:
        return 'project_specific'
    return 'other'


def extract_bash_commands(session_file: Path):
    """Yield all Bash command strings from a session JSONL file."""
    try:
        with open(session_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get('type') != 'assistant':
                    continue
                content = obj.get('message', {}).get('content', [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if isinstance(block, dict) and block.get('name') == 'Bash':
                        cmd = block.get('input', {}).get('command', '')
                        if cmd:
                            yield cmd
    except (OSError, PermissionError):
        return


def parse_sessions(since=None, until=None, files=None) -> dict:
    """Return dict of executable -> occurrence count from session history."""
    counts = {}
    sources = files if files is not None else list(iter_session_files(since, until))
    for session_file in sources:
        for command in extract_bash_commands(session_file):
            for sub in split_command(command):
                exe = extract_executable(sub)
                if exe:
                    counts[exe] = counts.get(exe, 0) + 1
    return counts


def classify_executables(counts: dict, allow_list: list) -> dict:
    """
    Classify executables into covered / safe_gap / dangerous_gap.
    Returns {'covered': [...], 'safe_gap': [...], 'dangerous_gap': [...]}.
    Each entry: {executable, count, category, pattern}.
    """
    from lib.dangerous import is_dangerous
    from lib.allowlist import is_covered

    result = {'covered': [], 'safe_gap': [], 'dangerous_gap': []}
    for exe, count in sorted(counts.items(), key=lambda x: -x[1]):
        entry = {
            'executable': exe,
            'count': count,
            'category': categorize(exe),
            'pattern': f'Bash({exe} *)',
        }
        if is_covered(exe, allow_list):
            result['covered'].append(entry)
        elif is_dangerous(exe):
            result['dangerous_gap'].append(entry)
        else:
            result['safe_gap'].append(entry)
    return result
