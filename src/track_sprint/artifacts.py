"""Local artifacts with explicit provenance, atomic metadata, and bounded cleanup."""
import hashlib
import json
from pathlib import Path
import shutil
import time


def stable_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
    temporary.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text())


def delete_session(path: Path, session_root: Path):
    """Delete only a validated immediate child of the app-owned session root."""
    root, target = session_root.resolve(), path.resolve()
    if target.parent != root or not target.name.startswith("session-"):
        raise ValueError("Refusing to remove a directory outside the session store.")
    shutil.rmtree(target, ignore_errors=True)


def clean_expired_sessions(root: Path, max_age_seconds=24 * 3600):
    if not root.exists():
        return
    for path in root.iterdir():
        if path.is_dir() and not path.is_symlink() and path.name.startswith("session-"):
            if time.time() - path.stat().st_mtime > max_age_seconds:
                delete_session(path, root)
