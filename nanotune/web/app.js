/* nanoTune — the page. No framework, no build step. */
"use strict";

const $ = (id) => document.getElementById(id);

let songs = [];        // the songs in the open folder
let current = -1;      // which one is playing
let shuffle = false;
let repeat = false;
let lastFolder = "";

// ---------------------------------------------------------------- helpers
async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({ error: "The answer was not understandable." }));
  if (!response.ok) throw new Error(body.error || "Something went wrong.");
  return body;
}

function post(path, payload) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
}

function toast(message, mood) {
  const box = document.createElement("div");
  box.className = "toast" + (mood ? " " + mood : "");
  box.innerHTML = '<button class="x">✕</button> ' + message;
  box.querySelector(".x").onclick = () => box.remove();
  $("toasts").appendChild(box);
  setTimeout(() => box.remove(), 7000);
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------------------------------------------------------------- folder
async function openFolder(path) {
  try {
    const data = await post("/api/open-folder", { path });
    if (!data.songs) throw new Error(data.error || "That folder could not be read.");
    lastFolder = data.folder;
    songs = data.songs;
    current = -1;
    $("hero").hidden = true;
    $("player").hidden = false;
    $("libraryBlock").hidden = false;
    $("libraryTitle").textContent = "The songs in " + data.name;
    $("libraryHint").textContent = data.total === 0 ? "" :
      data.total + " song" + (data.total === 1 ? "" : "s") +
      (data.skipped ? " — " + data.skipped + " other file" + (data.skipped === 1 ? "" : "s") + " left out" : "");
    renderLibrary();
    if (data.total === 0) {
      toast("No songs were found in that folder.", "bad");
    }
    $("folderInput").value = data.folder;
  } catch (err) {
    toast(String(err.message || err), "bad");
  }
}

// ---------------------------------------------------------------- library
function renderLibrary() {
  const box = $("library");
  box.innerHTML = "";
  songs.forEach((song, index) => {
    const playable = /\.(mp3|wav|ogg|oga|m4a|flac|aac|opus|webm)$/i.test(song.name);
    const row = document.createElement("div");
    row.className = "song" + (index === current ? " playing" : "") + (playable ? "" : " unplayable");
    row.innerHTML =
      '<div class="num">' + (index + 1) + "</div>" +
      '<div class="main">' +
        '<div class="title">' + escapeHtml(song.title) + "</div>" +
        '<div class="facts">' + (song.artist ? escapeHtml(song.artist) + " · " : "") +
        escapeHtml(song.what) + " · " + escapeHtml(song.size_text) + "</div>" +
      "</div>" +
      (playable ? "" : '<span class="tag">will not play</span>');
    row.onclick = () => {
      if (!playable) { toast("The browser does not know how to play " + escapeHtml(song.what) + ".", "bad"); return; }
      play(index);
    };
    box.appendChild(row);
  });
}

// ---------------------------------------------------------------- playing
function play(index) {
  if (index < 0 || index >= songs.length) return;
  current = index;
  const song = songs[index];
  $("audio").src = "/api/stream?path=" + encodeURIComponent(song.path);
  // Pick up where this song was stopped last time, unless it was the start or the end.
  api("/api/position?path=" + encodeURIComponent(song.path)).then((data) => {
    if (data.seconds > 5) $("audio").currentTime = data.seconds;
  }).catch(() => {});
  $("audio").play().catch(() => toast("The browser refused to start playing.", "bad"));
  $("nowTitle").textContent = song.title;
  $("nowArtist").textContent = (song.artist ? song.artist + " — " : "") + song.what +
    " · " + song.size_text;
  document.querySelectorAll(".song").forEach((row, i) => row.classList.toggle("playing", i === current));
  const playing = document.querySelector(".song.playing");
  if (playing) playing.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function nextSong(auto) {
  if (!songs.length) return;
  let index;
  if (shuffle && songs.length > 1) {
    do { index = Math.floor(Math.random() * songs.length); } while (index === current);
  } else {
    index = current + 1;
    if (index >= songs.length) {
      if (repeat) index = 0;
      else {
        $("nowSaid").textContent = "That was everything.";
        return;
      }
    }
  }
  play(index);
}

function prevSong() {
  if (!songs.length) return;
  play(current <= 0 ? songs.length - 1 : current - 1);
}

// ---------------------------------------------------------------- wiring
$("openBtn").onclick = () => openFolder($("folderInput").value.trim());
$("folderInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") openFolder($("folderInput").value.trim());
});
$("browseBtn").onclick = async () => {
  try {
    const data = await post("/api/pick-folder");
    if (data.ok) { $("folderInput").value = data.path; openFolder(data.path); }
    else toast(data.why || "No folder was chosen.", "bad");
  } catch (err) { toast(String(err.message || err), "bad"); }
};
$("folderBtn").onclick = () => { $("hero").hidden = false; $("folderInput").focus(); };

$("prevBtn").onclick = prevSong;
$("nextBtn").onclick = () => nextSong(false);
$("audio").addEventListener("ended", () => nextSong(true));
$("shuffleBtn").onclick = () => {
  shuffle = !shuffle;
  $("shuffleBtn").classList.toggle("on", shuffle);
  post("/api/toggles", { shuffle, repeat }).catch(() => {});
};
$("repeatBtn").onclick = () => {
  repeat = !repeat;
  $("repeatBtn").classList.toggle("on", repeat);
  post("/api/toggles", { shuffle, repeat }).catch(() => {});
};

// Every few seconds while playing, remember where the song is.
let lastSaved = 0;
$("audio").addEventListener("timeupdate", () => {
  if (current < 0 || !$("audio").src) return;
  const now = Date.now();
  if (now - lastSaved < 5000) return;
  lastSaved = now;
  const song = songs[current];
  if (song && !$("audio").paused) {
    post("/api/position", { path: song.path, seconds: $("audio").currentTime }).catch(() => {});
  }
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.onclick = () => btn.closest(".backdrop").hidden = true;
});
$("helpBtn").onclick = () => { $("helpModal").hidden = false; };
document.querySelectorAll(".backdrop").forEach((backdrop) => {
  backdrop.onclick = (event) => { if (event.target === backdrop) backdrop.hidden = true; };
});

// ---------------------------------------------------------------- start
(async () => {
  try {
    try {
      const toggles = await api("/api/settings-toggles");
      if (toggles.shuffle) { shuffle = true; $("shuffleBtn").classList.add("on"); }
      if (toggles.repeat) { repeat = true; $("repeatBtn").classList.add("on"); }
    } catch (err) { /* optional nicety */ }
    const data = await api("/api/folders");
    if (data.last_folder) {
      $("folderInput").value = data.last_folder;
      openFolder(data.last_folder);
    }
  } catch (err) { /* first visit — the page is asking */ }
})();
