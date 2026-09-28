"""The pages and the addresses the page talks to.

nanoTune hands files to the browser for playing, so the same rule as the rest
of the family applies twice over: only this app's own page may drive it, and
only songs that live in a folder you actually opened can ever be streamed —
a made-up path gets a refusal, not the music.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from . import APP_NAME, PLAYABLE, __version__, library, store
from .httpbase import App, Bytes, Error, Json

PORT = 8776

_OWN_ORIGINS = ("127.0.0.1", "localhost", "::1", "[::1]")


def create_app() -> App:
    app = App(APP_NAME, Path(__file__).parent / "web", version=__version__)

    def _from_local_page(request, require_json: bool = False) -> bool:
        origin = request.header("Origin")
        if origin:
            host = urlparse(origin).hostname or ""
            if host not in _OWN_ORIGINS:
                return False
        if require_json:
            content_type = (request.header("Content-Type") or "").split(";")[0].strip()
            if content_type != "application/json":
                return False
        return True

    def _in_known_folders(path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        for known in store.settings()["folders"]:
            try:
                resolved.relative_to(Path(known))
                return True
            except (ValueError, OSError):
                continue
        return False

    @app.get("/api/health")
    def health(_request):
        return Json({
            "ok": True, "app": APP_NAME, "version": __version__,
            "folders": store.settings()["folders"],
            "last_folder": store.settings()["last_folder"],
        })

    @app.get("/api/folders")
    def folders(_request):
        remembered = store.settings()
        return Json({
            "ok": True,
            "folders": remembered["folders"],
            "last_folder": remembered["last_folder"],
        })

    @app.post("/api/open-folder")
    def open_folder(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        where = str(payload.get("path") or "").strip()
        if not where:
            return Error("Say which folder to open first.")
        if not Path(where).is_dir():
            return Error("There is no folder at %s." % where)
        remembered = store.remember_folder(where)
        listing = library.scan(remembered)
        if not listing.get("ok"):
            return Error(listing.get("error", "That folder could not be read."))
        return Json(listing)

    @app.get("/api/settings-toggles")
    def get_toggles(_request):
        remembered = store.settings()
        return Json({"ok": True, "shuffle": remembered["shuffle"], "repeat": remembered["repeat"]})

    @app.post("/api/pick-folder")
    def pick_folder(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        from . import actions
        answer = actions.pick_folder_dialog()
        if not answer.get("ok"):
            return Json({"ok": False, "why": answer.get("why", "No folder was chosen.")})
        return Json({"ok": True, "path": answer["path"]})

    @app.post("/api/forget-folder")
    def forget_folder(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        remaining = store.forget_folder(payload.get("path", ""))
        return Json({"ok": True, "folders": remaining})

    @app.get("/api/list")
    def listing(request):
        where = request.q("path", "") or store.settings()["last_folder"]
        if not where:
            return Json({"ok": True, "folder": "", "name": "", "total": 0, "songs": [], "skipped": 0})
        result = library.scan(where)
        if not result.get("ok"):
            return Error(result.get("error", "That folder could not be read."))
        return Json(result)

    @app.get("/api/stream")
    def stream(request):
        path = Path(request.q("path", ""))
        if not path.is_file():
            return Error("That song is not there any more.")
        if not _in_known_folders(path):
            return Error("nanoTune only plays songs from a folder you opened here.")
        if path.suffix.lower() not in library.MIME_BY_SUFFIX and path.suffix.lower() not in PLAYABLE:
            return Error("That is not a kind of file the browser can play.")

        try:
            size = path.stat().st_size
        except OSError:
            return Error("That song could not be read.")

        mime = library.mime_for(path.name)
        range_header = request.header("Range") or ""
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if match and (match.group(1) or match.group(2)):
            start = int(match.group(1)) if match.group(1) else max(0, size - int(match.group(2)))
            end = int(match.group(2)) if match.group(1) and match.group(2) else size - 1
            end = min(end, size - 1)
            if start > end or start >= size:
                return Error("That part of the song does not exist.", 416)
            try:
                with path.open("rb") as handle:
                    handle.seek(start)
                    data = handle.read(end - start + 1)
            except OSError:
                return Error("That song could not be read.")
            piece = Bytes(data, mime)
            piece.status = 206
            piece.headers["Content-Range"] = "bytes %d-%d/%d" % (start, end, size)
            piece.headers["Accept-Ranges"] = "bytes"
            return piece

        try:
            data = path.read_bytes()
        except OSError:
            return Error("That song could not be read.")
        whole = Bytes(data, mime)
        whole.headers["Accept-Ranges"] = "bytes"
        return whole

    @app.post("/api/position")
    def set_position(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        saved = store.save_position(payload.get("path", ""), payload.get("seconds", 0))
        return Json({"ok": True, "saved": saved})

    @app.get("/api/position")
    def get_position(request):
        path = request.q("path", "")
        return Json({"ok": True, "seconds": store.position_of(path)})

    @app.post("/api/toggles")
    def set_toggles(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        saved = store.save_settings({"shuffle": payload.get("shuffle"), "repeat": payload.get("repeat")})
        return Json({"ok": True, "shuffle": saved["shuffle"], "repeat": saved["repeat"]})

    @app.post("/api/reveal")
    def reveal(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        from . import actions
        payload = request.json() or {}
        return Json(actions.reveal(payload.get("path", "")))

    return app


def main() -> None:
    app = create_app()
    app.serve(port=PORT)
