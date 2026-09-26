"""Everything nanoTune remembers between visits.

The folders of music you have opened, and which one was last — in
``~/.nanotune``. Deleting that folder makes nanoTune forget; your music was
never stored here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR_NAME = ".nanotune"

DEFAULT_SETTINGS = {
    # The folders of music you have opened, most recent first.
    "folders": [],
    # The one the page opens with.
    "last_folder": "",
}


def data_dir() -> Path:
    override = os.environ.get("NANOTUNE_HOME")
    base = Path(override) if override else Path.home() / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _settings_path() -> Path:
    return data_dir() / "settings.json"


def settings() -> dict:
    """What is remembered, with sensible answers for anything missing."""
    try:
        stored = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stored = {}
    out = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in stored:
            out[key] = stored[key]
    return out


def save_settings(patch: dict) -> dict:
    """Change what is remembered, and answer with the whole picture."""
    current = settings()
    if "folders" in patch:
        current["folders"] = _clean_folders(patch["folders"])
    if "last_folder" in patch:
        current["last_folder"] = str(patch["last_folder"] or "").strip()
    try:
        _settings_path().write_text(json.dumps(current, indent=2), encoding="utf-8")
    except OSError:
        pass  # a read-only home folder is not worth failing a song over
    return current


def _clean_folders(value) -> list[str]:
    """Folders that exist, with no duplicates, most recent first."""
    folders: list[str] = []
    for item in value if isinstance(value, list) else []:
        text = str(item or "").strip()
        if not text:
            continue
        path = Path(text)
        try:
            resolved = str(path.resolve())
        except OSError:
            continue
        if path.is_dir() and resolved not in folders:
            folders.append(resolved)
    return folders[:12]


def remember_folder(path) -> str:
    """A folder has been opened: put it at the front of the list."""
    where = str(Path(path).resolve())
    folders = [where] + [f for f in settings()["folders"] if f != where]
    save_settings({"folders": folders, "last_folder": where})
    return where


def forget_folder(path) -> list[str]:
    """Take a folder off the list. The music itself is never touched."""
    gone = str(Path(path).resolve())
    remaining = [f for f in settings()["folders"] if f != gone]
    save_settings({"folders": remaining})
    return remaining
