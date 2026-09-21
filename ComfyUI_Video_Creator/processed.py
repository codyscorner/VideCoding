"""Which source files already have a finished video in the Library.

A source counts as processed when a prompt-history entry records a result
made from it (``sources`` per result file, or the entry-level ``source`` that
pre-2.6.1 sidecars wrote) AND that result file is still sitting in one of the
Library's folders — so deleting a bad generation puts its source back in the
picker. Names are compared case-insensitively, as Windows does.
"""

import json
from pathlib import Path

from workflow_tools import HISTORY_SUFFIX

# history file -> (mtime, {result name -> source name})
_CACHE: dict[str, tuple[float, dict[str, str]]] = {}


def _result_sources(hist: Path) -> dict[str, str]:
    try:
        mtime = hist.stat().st_mtime
    except OSError:
        return {}
    cached = _CACHE.get(str(hist))
    if cached is not None and cached[0] == mtime:
        return cached[1]
    pairs: dict[str, str] = {}
    try:
        with open(hist, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = []
    for entry in data if isinstance(data, list) else []:
        if not isinstance(entry, dict):
            continue
        per_file = entry.get("sources") or {}
        for result in entry.get("results") or []:
            source = per_file.get(result) or entry.get("source") or ""
            if source:
                pairs[str(result).lower()] = str(source).lower()
    _CACHE[str(hist)] = (mtime, pairs)
    return pairs


def library_file_names(folders: list[str]) -> set[str]:
    names: set[str] = set()
    for folder in folders:
        if not (folder or "").strip():
            continue
        try:
            names.update(p.name.lower() for p in Path(folder).iterdir() if p.is_file())
        except OSError:
            continue
    return names


def processed_sources(workflow_dir: str, library_folders: list[str]) -> set[str]:
    """Lower-cased file names of every source that has a result in the Library."""
    root = Path((workflow_dir or "").strip()) if (workflow_dir or "").strip() else None
    if root is None or not root.is_dir():
        return set()
    present = library_file_names(library_folders)
    if not present:
        return set()
    done: set[str] = set()
    for hist in root.rglob(f"*{HISTORY_SUFFIX}"):
        for result, source in _result_sources(hist).items():
            if result in present:
                done.add(source)
    return done
