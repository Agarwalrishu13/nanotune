"""Reading a folder of music and saying what is in it.

No metadata library is parsed — a song is described by its own file name,
cleaned up the way people name their music: "Artist - Title.mp3" becomes an
artist and a title, anything else is just called what it is called. The folder
is scanned once per request, so the list is always the truth: add a song and
it is there, take one away and it is gone.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import PLAYABLE

MAX_SONGS = 2000

SKIP_DIRS = {
    "$RECYCLE.BIN", "System Volume Information", "__pycache__",
    "node_modules", ".git", ".venv", "venv", "AppData",
}

MIME_BY_SUFFIX = {
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".oga": "audio/ogg",
    ".m4a": "audio/mp4", ".flac": "audio/flac", ".aac": "audio/aac",
    ".opus": "audio/ogg", ".webm": "audio/webm",
}

KIND_WORDS = {
    ".mp3": "an MP3", ".wav": "a WAV", ".ogg": "an OGG", ".oga": "an OGG",
    ".m4a": "an M4A", ".flac": "a FLAC", ".aac": "an AAC", ".opus": "an Opus",
    ".webm": "a WebM audio",
}


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return "%d %s" % (value, unit) if unit == "bytes" else "%.1f %s" % (value, unit)
        value /= 1024
    return "%d bytes" % size


def split_name(name: str) -> dict:
    """'Artist - Title.mp3' -> artist and title; anything else is honest."""
    stem = Path(name).stem
    for separator in (" - ", " – ", " — "):
        if separator in stem:
            artist, title = stem.split(separator, 1)
            artist, title = artist.strip(), title.strip()
            if artist and title:
                return {"artist": artist, "title": title}
    return {"artist": "", "title": stem}


def mime_for(name: str) -> str:
    return MIME_BY_SUFFIX.get(Path(name).suffix.lower(), "application/octet-stream")


def kind_word(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return KIND_WORDS.get(suffix, "a music file")


def scan(folder) -> dict:
    """The songs in one folder (and its sub-folders), ready to be played."""
    target = Path(folder)
    if not target.is_dir():
        return {"ok": False, "error": "There is no folder at %s" % folder}

    songs: list[dict] = []
    skipped_kinds = 0
    # os.walk directly — materialising it first would walk every folder before
    # the pruning below could skip the hidden ones.
    for current, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            suffix = Path(name).suffix.lower()
            if suffix in MIME_BY_SUFFIX:
                pass
            elif suffix in PLAYABLE:
                pass  # playable but unknown mime — still offered honestly
            else:
                if name.startswith("."):
                    continue
                skipped_kinds += 1
                continue
            full = Path(current) / name
            try:
                size = full.stat().st_size
            except OSError:
                continue
            bits = split_name(name)
            songs.append({
                "path": str(full),
                "name": name,
                "artist": bits["artist"],
                "title": bits["title"],
                "what": kind_word(name),
                "mime": mime_for(name),
                "size": size,
                "size_text": human_size(size),
                "folder": str(full.parent),
            })
            if len(songs) >= MAX_SONGS:
                break
        if len(songs) >= MAX_SONGS:
            break

    songs.sort(key=lambda song: song["name"].lower())
    return {
        "ok": True,
        "folder": str(target.resolve()),
        "name": target.name,
        "total": len(songs),
        "songs": songs,
        "skipped": skipped_kinds,
    }
