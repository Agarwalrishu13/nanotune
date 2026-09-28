"""nanoTune's tests, end to end: real folders, real bytes, real HTTP.

The library's judgement (what counts as a song, how names are cleaned up),
the store's memory, and the whole app over real HTTP — including the two rules
that matter most here: another website cannot drive it, and no song outside a
folder you opened can ever be streamed, not even with a made-up path.
"""

import json
import os
import tempfile
import threading
import time
import unittest
import unittest.mock
import urllib.request
from pathlib import Path

from nanotune import library, server, store


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "abba - dancing queen.mp3").write_bytes(b"mp3")
        (self.root / "song.wav").write_bytes(b"wav")
        (self.root / "bonus" ).mkdir()
        (self.root / "bonus" / "deep track.flac").write_bytes(b"flac")
        (self.root / "not a song.txt").write_text("hello", encoding="utf-8")
        (self.root / ".hidden dir").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def names(self, **kwargs):
        return [song["name"] for song in library.scan(self.root, **kwargs)["songs"]]

    def test_songs_are_found_and_other_files_are_not(self):
        names = self.names()
        self.assertIn("abba - dancing queen.mp3", names)
        self.assertIn("song.wav", names)
        self.assertNotIn("not a song.txt", names)

    def test_sub_folders_are_included(self):
        self.assertIn("deep track.flac", self.names())

    def test_hidden_folders_are_skipped(self):
        (self.root / ".hidden dir" / "secret.mp3").write_bytes(b"x")
        self.assertNotIn("secret.mp3", self.names())

    def test_the_list_is_alphabetical_regardless_of_case(self):
        names = self.names()
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_a_folder_that_is_not_there_is_explained(self):
        result = library.scan(self.root / "nope")
        self.assertFalse(result["ok"])
        self.assertIn("no folder", result["error"].lower())

    def test_names_are_cleaned_into_artist_and_title(self):
        bits = library.split_name("abba - dancing queen.mp3")
        self.assertEqual(bits, {"artist": "abba", "title": "dancing queen"})
        plain = library.split_name("whatever.mp3")
        self.assertEqual(plain, {"artist": "", "title": "whatever"})

    def test_every_song_says_what_it_is(self):
        result = library.scan(self.root)
        by_name = {song["name"]: song for song in result["songs"]}
        self.assertEqual(by_name["abba - dancing queen.mp3"]["what"], "an MP3")
        self.assertEqual(by_name["song.wav"]["what"], "a WAV")
        self.assertEqual(by_name["deep track.flac"]["what"], "a FLAC")

    def test_the_mime_is_what_the_browser_expects(self):
        self.assertEqual(library.mime_for("x.mp3"), "audio/mpeg")
        self.assertEqual(library.mime_for("x.flac"), "audio/flac")

    def test_sizes_come_in_plain_words(self):
        library.human_size(10)  # smoke
        self.assertEqual(library.human_size(0), "0 bytes")
        self.assertTrue(library.human_size(5 * 1024 * 1024).endswith("MB"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        patch = unittest.mock.patch.dict(os.environ, {"NANOTUNE_HOME": self._tmp.name})
        patch.start()
        self.addCleanup(patch.stop)

    def test_nothing_is_remembered_at_first(self):
        self.assertEqual(store.settings()["folders"], [])
        self.assertEqual(store.settings()["last_folder"], "")

    def test_an_opened_folder_is_remembered_and_goes_first(self):
        store.remember_folder(self._tmp.name)
        again = store.remember_folder(tempfile.mkdtemp(dir=self._tmp.name))
        self.assertEqual(store.settings()["folders"][0], again)
        self.assertEqual(store.settings()["last_folder"], again)

    def test_a_folder_that_does_not_exist_is_never_remembered(self):
        store.save_settings({"folders": [r"Z:\nowhere\at\all"]})
        self.assertEqual(store.settings()["folders"], [])

    def test_forgetting_removes_only_that_folder(self):
        first = store.remember_folder(self._tmp.name)
        second = store.remember_folder(tempfile.mkdtemp(dir=self._tmp.name))
        remaining = store.forget_folder(first)
        self.assertEqual(remaining, [second])


class ServerTestCase(unittest.TestCase):
    """The whole app over real HTTP, on this machine only."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        patch = unittest.mock.patch.dict(
            os.environ, {"NANOTUNE_HOME": str(Path(cls._tmp.name) / "home")})
        patch.start()
        cls._patch = patch

        cls.music = Path(cls._tmp.name) / "Music"
        cls.music.mkdir()
        (cls.music / "one.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 512)
        (cls.music / "two - song.ogg").write_bytes(b"OggS" + b"\x00" * 512)
        (cls.music / "notes.txt").write_text("not a song", encoding="utf-8")

        cls.app = server.create_app()
        import nanotune.httpbase as httpbase
        cls.port = httpbase.free_port(8776)
        cls.base = "http://127.0.0.1:%d" % cls.port
        threading.Thread(target=cls.app.serve, kwargs={
            "host": "127.0.0.1", "port": cls.port, "open_browser": False, "quiet": True,
        }, daemon=True).start()
        for _ in range(80):
            try:
                cls.get("/api/health")
                return
            except Exception:
                time.sleep(0.05)
        raise RuntimeError("the test server never came up")

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls._patch.stop()
        cls._tmp.cleanup()

    @classmethod
    def get(cls, path, headers=None):
        request = urllib.request.Request(cls.base + path, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read(), response.status, dict(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.read(), exc.code, dict(exc.headers)

    @classmethod
    def post(cls, path, payload=None, headers=None):
        request = urllib.request.Request(
            cls.base + path, data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read(), response.status
        except urllib.error.HTTPError as exc:
            return exc.read(), exc.code

    @staticmethod
    def body(raw):
        return json.loads(raw.decode("utf-8"))


class ServerBasicsTests(ServerTestCase):
    def test_health_says_who_it_is(self):
        raw, status, _ = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(self.body(raw)["app"], "nanoTune")

    def test_opening_a_folder_lists_its_songs(self):
        raw, status = self.post("/api/open-folder", {"path": str(self.music)})
        self.assertEqual(status, 200)
        data = self.body(raw)
        self.assertEqual(data["total"], 2)
        self.assertEqual([s["name"] for s in data["songs"]],
                         ["one.mp3", "two - song.ogg"])
        self.assertEqual(data["songs"][1]["artist"], "two")

    def test_the_opened_folder_is_remembered_for_next_time(self):
        self.post("/api/open-folder", {"path": str(self.music)})
        raw, status, _ = self.get("/api/folders")
        data = self.body(raw)
        self.assertEqual(data["last_folder"], str(self.music.resolve()))
        self.assertIn(str(self.music.resolve()), data["folders"])

    def test_a_folder_that_is_not_there_is_refused(self):
        raw, status = self.post("/api/open-folder", {"path": r"Z:\nowhere"})
        self.assertEqual(status, 400)

    def test_the_page_and_its_files_are_served(self):
        raw, status, _ = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"nanoTune", raw)


class StreamTests(ServerTestCase):
    def test_a_song_streams_with_its_type(self):
        self.post("/api/open-folder", {"path": str(self.music)})
        raw, status, headers = self.get(
            "/api/stream?path=" + urllib.request.quote(str(self.music / "one.mp3")))
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "audio/mpeg")
        self.assertEqual(raw[:2], b"\xff\xfb")

    def test_seeking_asks_for_a_part_and_gets_exactly_that_part(self):
        self.post("/api/open-folder", {"path": str(self.music)})
        raw, status, headers = self.get(
            "/api/stream?path=" + urllib.request.quote(str(self.music / "one.mp3")),
            headers={"Range": "bytes=10-19"})
        self.assertEqual(status, 206)
        self.assertEqual(len(raw), 10)
        self.assertEqual(headers.get("Content-Range"), "bytes 10-19/%d" % (512 + 2))

    def test_a_song_outside_any_opened_folder_is_refused(self):
        elsewhere = Path(self._tmp.name) / "elsewhere.mp3"
        elsewhere.write_bytes(b"x" * 64)
        raw, status, _ = self.get(
            "/api/stream?path=" + urllib.request.quote(str(elsewhere)))
        self.assertEqual(status, 400)
        self.assertIn("opened", self.body(raw)["error"])

    def test_a_made_up_path_is_refused(self):
        raw, status, _ = self.get(
            "/api/stream?path=" + urllib.request.quote(str(self.music / "ghost.mp3")))
        self.assertEqual(status, 400)

    def test_a_file_that_is_not_a_song_is_refused(self):
        self.post("/api/open-folder", {"path": str(self.music)})
        raw, status, _ = self.get(
            "/api/stream?path=" + urllib.request.quote(str(self.music / "notes.txt")))
        self.assertEqual(status, 400)


class LocalPageGuardTests(ServerTestCase):
    """Another website must not be able to drive this app."""

    def test_opening_a_folder_from_a_foreign_page_is_refused(self):
        raw, status = self.post("/api/open-folder", {"path": str(self.music)},
                                headers={"Origin": "https://evil.example"})
        self.assertEqual(status, 403)

    def test_streaming_is_get_so_the_page_can_use_it(self):
        # GET /api/stream is the one address a browser <audio> needs; the
        # folder gate above is what keeps it honest.
        self.post("/api/open-folder", {"path": str(self.music)}, headers={"Origin": self.base})
        raw, status, _ = self.get(
            "/api/stream?path=" + urllib.request.quote(str(self.music / "one.mp3")))
        self.assertEqual(status, 200)

    def test_a_mutation_without_json_is_refused(self):
        request = urllib.request.Request(
            self.base + "/api/forget-folder", data=b"hello", method="POST",
            headers={"Content-Type": "text/plain", "Origin": self.base})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()


class PositionTests(ServerTestCase):
    """Resume where you stopped: positions are remembered per song."""

    @classmethod
    def setUpClass(cls):
        ServerTestCase.setUpClass()
        cls.song = Path(cls._tmp.name) / "resume-song.mp3"
        cls.song.write_bytes(b"mp3")

    def test_a_position_is_remembered_and_replaced(self):
        store.save_position(self.song, 91.7)
        self.assertEqual(store.position_of(self.song), 91)
        store.save_position(self.song, 130.2)
        self.assertEqual(store.position_of(self.song), 130)

    def test_an_unknown_song_starts_from_the_top(self):
        self.assertEqual(store.position_of(self.song / "ghost.mp3"), 0)

    def test_silly_positions_are_ignored(self):
        store.save_position(self.song, -5)
        self.assertEqual(store.position_of(self.song), 0)
        store.save_position(self.song, 10 ** 9)
        self.assertEqual(store.position_of(self.song), 0)  # longer than a day: nonsense

    def test_positions_of_deleted_songs_are_dropped(self):
        ghost = Path(self._tmp.name) / "ghost.mp3"
        ghost.write_bytes(b"x")
        store.save_position(ghost, 30)
        ghost.unlink()
        store.save_position(self.song, 12)  # a clean-up pass runs on the next save
        self.assertEqual(store.position_of(ghost), 0)

    def test_toggles_are_remembered(self):
        store.save_settings({"shuffle": True, "repeat": True})
        self.assertTrue(store.settings()["shuffle"])
        self.assertTrue(store.settings()["repeat"])

    def test_over_http(self):
        store.save_settings({"positions": {}})  # start from a clean slate
        raw, status, _ = self.get("/api/position?path=" + urllib.request.quote(str(self.song)))
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw.decode())["seconds"], 0)
        raw, status = self.post("/api/position", {"path": str(self.song), "seconds": 42})
        self.assertEqual(status, 200)
        raw, status, _ = self.get("/api/position?path=" + urllib.request.quote(str(self.song)))
        self.assertEqual(json.loads(raw.decode())["seconds"], 42)