"""Reuse genuine completed analyses only after their exact source is uploaded."""
from pathlib import Path

from .artifacts import read_json


def find_cached_analysis(root: Path, video_hash: str):
    if not root.exists():
        return None
    for directory in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not directory.is_dir() or not (directory/'manifest.json').exists():
            continue
        try:
            manifest = read_json(directory/'manifest.json')
            summary = read_json(directory/'summary.json')
            if (manifest['input_sha256'] == video_hash == summary['video']['sha256']
                    and manifest['analysis_id'] == summary['analysis_id']
                    and summary['quality'] != 'insufficient'
                    and all((directory/name).exists() for name in ('original.mp4', 'annotated.mp4', 'landmarks.npz', 'series.json', 'frames'))):
                return directory, summary['config']
        except (OSError, ValueError, KeyError):
            continue
    return None
