"""Persistence — the session playlist plus named, saved playlists.

Everything is stored as JSON under the app data folder:
    <appdata>/session.json            the working "Library" list
    <appdata>/playlists/<name>.json   one file per named playlist

Track order is preserved; files that no longer exist on disk are dropped on load.
Named-playlist files are keyed by a URL-quoted form of the name, so any name is a
safe, reversible filename.
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from urllib.parse import quote, unquote

from PyQt6.QtCore import QStandardPaths

from core.library import Track

_SESSION_FILE = "session.json"
_PLAYLISTS_DIR = "playlists"

_FIELDS = {f.name for f in dataclasses.fields(Track)}


# --------------------------------------------------------------- locations
def _data_dir() -> Path:
    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    path = Path(base) if base else Path.home() / ".music_player"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_path() -> Path:
    return _data_dir() / _SESSION_FILE


def _playlists_dir() -> Path:
    path = _data_dir() / _PLAYLISTS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _playlist_path(name: str) -> Path:
    return _playlists_dir() / f"{quote(name, safe='')}.json"


# --------------------------------------------------------- (de)serialization
def _tracks_to_data(tracks: list[Track]) -> list[dict]:
    return [dataclasses.asdict(t) for t in tracks]


def _tracks_from_data(data) -> list[Track]:
    tracks: list[Track] = []
    if not isinstance(data, list):
        return tracks
    for entry in data:
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        if not os.path.exists(entry["path"]):
            continue  # file moved/deleted since it was saved
        fields = {k: v for k, v in entry.items() if k in _FIELDS}
        try:
            tracks.append(Track(**fields))
        except TypeError:
            continue
    return tracks


def _write_json(path: Path, data) -> None:
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8"
        )
    except OSError:
        pass  # persistence is best-effort


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ session
def save_session(tracks: list[Track]) -> None:
    _write_json(_session_path(), _tracks_to_data(tracks))


def load_session() -> list[Track]:
    return _tracks_from_data(_read_json(_session_path()))


# ----------------------------------------------------------- named playlists
def list_playlists() -> list[str]:
    """Names of all saved playlists, sorted case-insensitively."""
    names = []
    for f in _playlists_dir().glob("*.json"):
        names.append(unquote(f.stem))
    return sorted(names, key=str.lower)


def playlist_exists(name: str) -> bool:
    return _playlist_path(name).exists()


def save_playlist(name: str, tracks: list[Track]) -> None:
    _write_json(_playlist_path(name), _tracks_to_data(tracks))


def load_playlist(name: str) -> list[Track]:
    return _tracks_from_data(_read_json(_playlist_path(name)))


def delete_playlist(name: str) -> None:
    try:
        _playlist_path(name).unlink(missing_ok=True)
    except OSError:
        pass


def rename_playlist(old: str, new: str) -> bool:
    src = _playlist_path(old)
    dst = _playlist_path(new)
    if not src.exists() or dst.exists():
        return False
    try:
        src.rename(dst)
        return True
    except OSError:
        return False


def remove_path_everywhere(path: str) -> int:
    """Drop a file path from the session and every named playlist on disk.

    Used when a track's file has gone missing. Returns the number of stored
    lists (session + playlists) that were changed.
    """
    changed = 0

    session = _read_json(_session_path())
    if isinstance(session, list):
        kept = [e for e in session if not (isinstance(e, dict) and e.get("path") == path)]
        if len(kept) != len(session):
            _write_json(_session_path(), kept)
            changed += 1

    for name in list_playlists():
        p = _playlist_path(name)
        data = _read_json(p)
        if isinstance(data, list):
            kept = [e for e in data if not (isinstance(e, dict) and e.get("path") == path)]
            if len(kept) != len(data):
                _write_json(p, kept)
                changed += 1
    return changed


def add_to_playlist(name: str, tracks: list[Track]) -> int:
    """Merge tracks into a playlist (creating it if needed), skipping paths
    already present. Returns how many were actually added."""
    existing = load_playlist(name) if playlist_exists(name) else []
    have = {t.path for t in existing}
    added = [t for t in tracks if t.path not in have]
    if added or not playlist_exists(name):
        save_playlist(name, existing + added)
    return len(added)
