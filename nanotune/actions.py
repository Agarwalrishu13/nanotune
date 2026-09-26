"""The two things nanoTune does outside the browser, in plain words.

Reveal a song's folder, and ask the operating system for a folder with its own
window. Nothing here ever changes a file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def reveal(path) -> dict:
    """Show the folder the song lives in, with the song chosen."""
    target = Path(path)
    if not target.exists():
        return {"ok": False, "said": "That song is not there any more."}
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent)])
    except OSError as exc:
        return {"ok": False, "said": "The computer refused (%s)." % exc}
    return {"ok": True, "said": "Showing the folder it lives in."}


def pick_folder_dialog() -> dict:
    """Ask the operating system for a folder, if this computer can do that."""
    if sys.platform == "win32":
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$f.Description = 'Which folder is your music in?';"
            "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.SelectedPath }"
        )
        try:
            done = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", script],
                capture_output=True, text=True, timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "why": "The folder window did not open."}
        chosen = (done.stdout or "").strip()
        if chosen and Path(chosen).is_dir():
            return {"ok": True, "path": chosen}
        return {"ok": False, "why": "No folder was chosen."}
    if sys.platform == "darwin":
        script = 'osascript -e \'POSIX path of (choose folder with prompt "Which folder is your music in?")\''
        try:
            done = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "why": "The folder window did not open."}
        chosen = (done.stdout or "").strip()
        if chosen and Path(chosen).is_dir():
            return {"ok": True, "path": chosen}
    return {"ok": False, "why": "This computer cannot open a folder window from here — type the folder instead."}
