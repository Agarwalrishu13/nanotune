<div align="center">

# nanoTune

**Your music, one page, no account.** No uploads, no sign-in, no "premium".

The music is already on your computer. The browser already knows how to play
it. nanoTune is the page in between: point it at a folder, and every song in
it — sub-folders too — is there to press play on. Next, previous, shuffle,
repeat. That is the whole thing.

[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.9+-58a6ff.svg)]()
[![dependencies](https://img.shields.io/badge/required%20deps-0-f0883e.svg)]()
[![tests](https://img.shields.io/badge/tests-26%20passing-3ddc97.svg)]()

</div>

---

> **Part of [the nano family](https://github.com/Agarwalrishu13/nano)** — eleven offline-first apps for people who do not code. This is the map of the whole project.


## What this is, in one paragraph

Music players mostly want to sell you something — a subscription, a sign-in, a
"library" that quietly moves your files into somebody else's cloud. nanoTune
does none of that. It reads the folder you point it at, lists the songs it
finds (cleaning up `Artist - Title.mp3` names into artist and title), and
plays them in the page. A song that the browser cannot play is listed honestly
with a *will not play* tag, not hidden. When you close it, nothing has changed
anywhere.

---

## Use it

1. Install Python if you do not have it — [python.org/downloads](https://www.python.org/downloads/).
2. Download this repo and unzip it.
3. **Windows:** double-click `run.bat`. **macOS / Linux:** `./run.sh`.
4. Your browser opens at `http://127.0.0.1:8776`.

<details>
<summary>Prefer the command line? (you do not need to)</summary>

```bash
python start.py                        # start and open the browser
python -m nanotune doctor              # say what this computer has, and stop
python -m nanotune --port 9000 --no-browser
```

</details>

---

## What you can do with it

| thing | how |
|---|---|
| **Open your music** | Type a folder or press *Choose a folder in a window* — your operating system's own picker. It is remembered for next time. |
| **Play a song** | Press it. Everything plays in the page; seeking works, even in long files. |
| **Move through the evening** | ⏭ next · ⏮ previous · 🔀 shuffle · 🔁 repeat everything. |
| **See what a song is** | `Artist - Title.mp3` shows as artist and title; every song also says what kind it is (an MP3, a FLAC…) and how big. |
| **Find the file later** | A song's folder is one press away, with the song chosen in it. |

### Things it does that you would not expect from a toy

- **The list is always the truth.** The folder is read when you open it — add
  a song and it is there, take one away and it is gone. Nothing is indexed,
  so there is no stale library and no "missing file" mystery.
- **No song leaves the machine.** The browser streams from this computer, to
  this computer. A song outside a folder you opened cannot be streamed, even
  with a made-up address — there is a test that proves it.
- **Unplayable is said, not hidden.** If the browser cannot play a kind of
  file, it stays in the list with an honest tag.
- **Another website cannot drive it.** Every action checks that the request
  came from this app's own page on this computer.

---

## What it does not do, honestly

- **It does not organise your files.** Nothing is moved, renamed or tagged.
- **It does not read song metadata.** An MP3's hidden tags are ignored — the
  file name is what you get. That keeps it honest about what it knows.
- **It does not make a library.** Close it, and the next visit opens with the
  last folder — nothing more is remembered.
- **A few rare formats will not play.** The browser decides what it can play;
  nanoTune never pretends otherwise.

---

## Where your settings live

```
~/.nanotune/
  settings.json    the folders you opened, and which one was last
```

Delete that folder and nanoTune forgets everything. The music was never
stored there.

---

## The rest of the family

| app | what it is for |
|---|---|
| 🧭 [nanoHome](https://github.com/Agarwalrishu13/nanohome) | one front door for every nano app on this computer |
| 🧠 [nanoLaama](https://github.com/Agarwalrishu13/nanolaama) | talk to an AI on your own computer, offline |
| 📚 [nanoDoc](https://github.com/Agarwalrishu13/nanodoc) | drop in a document, ask it anything |
| 📊 [nanoLearn](https://github.com/Agarwalrishu13/nanolearn) | drop a spreadsheet, get an answer machine |
| 🔊 [nanoSay](https://github.com/Agarwalrishu13/nanosay) | have anything read out loud |
| 🧲 [nanoPick](https://github.com/Agarwalrishu13/nanopick) | find your files by saying what you remember |
| 🎵 [**nanoTune**](https://github.com/Agarwalrishu13/nanotune) | your music, one page, no account — *this repo* |
| 🧰 [nanoWrap](https://github.com/Agarwalrishu13/nanowrap) | the best-known programs, with ready-made buttons |
| ⌨️ [nanoShell](https://github.com/Agarwalrishu13/nanoshell) | any program at all, with words instead of flags |
| 🗂 [nanoGit](https://github.com/Agarwalrishu13/nanogit) | your folder, kept safe without learning git |
| 🖥 [nanoDesk](https://github.com/Agarwalrishu13/nanodesk) | every nano-style app you have, one click away |
| 🃏 [nonoForge](https://github.com/Agarwalrishu13/nonoforge) | pick a card, press one button, you have an app |

And underneath them, for people who want to see the gears: [nanollama.c](https://github.com/Agarwalrishu13/nanollama.c) (the C engine), [nanobrain](https://github.com/Agarwalrishu13/nanobrain) (training from scratch), [nanoforge](https://github.com/Agarwalrishu13/nanoforge) (the model studio) and [nanorl](https://github.com/Agarwalrishu13/nanorl) (alignment).

The map of the whole project — what each app is for, and how they fit together — lives in [the nano family](https://github.com/Agarwalrishu13/nano).
MIT license. Made for people who do not write code, by someone who does.
