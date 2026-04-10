import json
import fcntl
from pathlib import Path
from datetime import datetime, timezone

DANGEROUS_EXECUTABLES = {
    'rm', 'shred', 'wipefs', 'truncate',
    'dd', 'mkfs', 'fdisk', 'parted', 'format',
    'sudo', 'su', 'doas',
    'nc', 'ncat', 'socat',
}

QUEUE_DIR = Path.home() / '.claude' / 'allowlist-manager'
QUEUE_FILE = QUEUE_DIR / 'skipped.jsonl'


def is_dangerous(executable: str) -> bool:
    return Path(executable).name in DANGEROUS_EXECUTABLES


def append_to_queue(command: str, executable: str, session: str = '') -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        'command': command,
        'executable': executable,
        'session': session,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    with open(QUEUE_FILE, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(json.dumps(entry) + '\n')
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def read_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    entries = []
    with open(QUEUE_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def write_queue(entries: list) -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
