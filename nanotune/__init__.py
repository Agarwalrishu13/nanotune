"""nanoTune — your music, one page, no account.

The whole idea in one sentence: the music is already on this computer, and the
browser already knows how to play it — the only thing missing is a page that
points at the folder and presses play.

nanoTune looks in the folder you choose, lists the songs it finds, and plays
them right there: next, previous, shuffle, repeat. It never moves, renames or
changes a single file, and nothing is uploaded anywhere.
"""

APP_NAME = "nanoTune"
__version__ = "0.2.0"

TAGLINE = "your music, one page, no account"

# The kinds of audio a browser can usually play without any help.
PLAYABLE = (".mp3", ".wav", ".ogg", ".oga", ".m4a", ".flac", ".aac", ".opus", ".webm")

__all__ = ["APP_NAME", "__version__", "TAGLINE", "PLAYABLE"]
