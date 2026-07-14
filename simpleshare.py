#!/usr/bin/env python3
"""
SimpleShare — Local Network File Transfer
No internet. No accounts. No installs beyond Python.

Highlights
----------
* Pure Python standard library — zero dependencies.
* Streaming, memory-safe uploads: files are written to disk in chunks as they
  arrive, so multi-gigabyte videos transfer without exhausting RAM.
* Threaded server: multiple devices can upload/download at the same time.
* Safe filenames: path components are stripped and name collisions auto-rename
  (photo.jpg -> photo (1).jpg) instead of silently overwriting.
* A responsive web UI that feels native on phones and roomy on desktops.
"""

import os
import re
import sys
import json
import socket
import mimetypes
import argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_PORT = 8080
DEFAULT_DIR = "shared_files"
CHUNK = 256 * 1024  # 256 KB streaming chunk

# ─── Embedded Web UI ──────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0ea5e9">
<title>SimpleShare</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg1: #0b1220; --bg2: #070c16;
    --surface: rgba(23, 33, 54, .72);
    --surface-solid: #131c30;
    --raised: #1b2740;
    --border: rgba(120, 150, 210, .18);
    --border-strong: #38bdf8;
    --accent: #38bdf8; --accent-2: #22d3ee;
    --accent-ink: #04121e;
    --text: #eaf1fb; --sub: #9fb2cf; --muted: #64769a;
    --ok: #34d399; --danger: #f87171; --warn: #fbbf24;
    --radius: 20px; --radius-sm: 13px;
    --shadow: 0 24px 60px -30px rgba(0,0,0,.85);
  }
  @media (prefers-color-scheme: light) {
    :root {
      --bg1: #eef4fb; --bg2: #e4ecf7;
      --surface: rgba(255,255,255,.86);
      --surface-solid: #ffffff;
      --raised: #f1f5fb;
      --border: rgba(14, 116, 190, .16);
      --accent: #0ea5e9; --accent-2: #0891b2;
      --accent-ink: #ffffff;
      --text: #0f1e33; --sub: #47597a; --muted: #7185a5;
      --shadow: 0 24px 60px -34px rgba(30,60,120,.4);
    }
  }

  html { -webkit-text-size-adjust: 100%; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, sans-serif;
    color: var(--text);
    background:
      radial-gradient(1100px 620px at 88% -10%, rgba(56,189,248,.16), transparent 58%),
      radial-gradient(900px 560px at 0% 108%, rgba(34,211,238,.13), transparent 55%),
      linear-gradient(180deg, var(--bg1), var(--bg2));
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    padding-bottom: calc(28px + env(safe-area-inset-bottom));
    overflow-x: hidden;   /* safety net: never scroll the page sideways */
  }
  html { overflow-x: hidden; }

  /* ---------- Header ---------- */
  header {
    position: sticky; top: 0; z-index: 20;
    backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
    background: linear-gradient(180deg, rgba(11,18,32,.82), rgba(11,18,32,.5));
    border-bottom: 1px solid var(--border);
    padding: 14px max(16px, env(safe-area-inset-left)) 14px;
  }
  @media (prefers-color-scheme: light) {
    header { background: linear-gradient(180deg, rgba(255,255,255,.9), rgba(255,255,255,.6)); }
  }
  .head-inner {
    max-width: 900px; margin: 0 auto;
    display: flex; align-items: center; gap: 12px;
  }
  .mark {
    width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
    display: grid; place-items: center; font-size: 20px;
    background: linear-gradient(150deg, var(--accent), var(--accent-2));
    box-shadow: 0 8px 20px -8px rgba(56,189,248,.75);
  }
  .titles h1 { font-size: 1.12rem; font-weight: 700; letter-spacing: -.01em; }
  .titles p { font-size: .76rem; color: var(--sub); margin-top: 1px; }
  .head-spacer { flex: 1; }
  .conn-pill {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: .74rem; font-weight: 600; color: var(--sub);
    background: var(--surface-solid); border: 1px solid var(--border);
    padding: 7px 12px; border-radius: 999px; white-space: nowrap;
  }
  .conn-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok);
    box-shadow: 0 0 0 4px rgba(52,211,153,.16); }

  .wrap { max-width: 900px; margin: 0 auto; padding: 22px max(16px, env(safe-area-inset-left)); }

  .card {
    background: var(--surface);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border); border-radius: var(--radius);
    padding: 20px; margin-bottom: 18px; box-shadow: var(--shadow);
  }
  .card h2 {
    font-size: .74rem; font-weight: 700; color: var(--sub);
    text-transform: uppercase; letter-spacing: .09em; margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
  }

  /* ---------- Connect card ---------- */
  .url-row { display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap; }
  .url-box {
    flex: 1; min-width: 0; background: var(--raised); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 13px 16px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1.02rem; font-weight: 600; color: var(--accent);
    word-break: break-all; display: flex; align-items: center;
  }
  .hint { font-size: .78rem; color: var(--muted); margin-top: 11px; line-height: 1.5; }

  .btn {
    -webkit-appearance: none; appearance: none;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
    color: var(--accent-ink); border: none; cursor: pointer;
    padding: 12px 20px; border-radius: var(--radius-sm);
    font-weight: 700; font-size: .9rem; font-family: inherit;
    transition: transform .14s ease, filter .18s ease, box-shadow .18s ease;
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    white-space: nowrap; min-height: 46px;
  }
  .btn:hover { filter: brightness(1.06); }
  .btn:active { transform: translateY(1px); }
  .btn:disabled { opacity: .5; cursor: default; filter: none; }
  .btn-ghost {
    background: transparent; color: var(--text);
    border: 1px solid var(--border); box-shadow: none;
  }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent); filter: none; }
  .btn-sm { padding: 9px 14px; font-size: .82rem; min-height: 40px; }
  .btn-icon { padding: 9px 12px; min-height: 40px; }
  .btn-danger { color: var(--danger); border-color: rgba(248,113,113,.4); }
  .btn-danger:hover { background: var(--danger); color: #fff; border-color: transparent; }

  /* ---------- Two column layout ---------- */
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  /* Grid items default to min-width:auto, which refuses to shrink below their
     content and causes sideways overflow on mobile when a long filename lands
     in the nowrap upload row. Allowing them to shrink lets text truncate. */
  .grid > * { min-width: 0; }
  @media (max-width: 720px) { .grid { grid-template-columns: 1fr; gap: 16px; } }

  /* ---------- Drop zone ---------- */
  .drop {
    position: relative; border: 2px dashed var(--border); border-radius: var(--radius-sm);
    padding: 30px 18px; text-align: center; cursor: pointer;
    transition: border-color .2s, background .2s, transform .1s;
  }
  .drop:hover, .drop.over { border-color: var(--accent); background: rgba(56,189,248,.07); }
  .drop.over { transform: scale(1.01); }
  .drop .ic { font-size: 2rem; }
  .drop .big { margin-top: 8px; font-weight: 600; font-size: .96rem; }
  .drop .big strong { color: var(--accent); }
  .drop .sm { color: var(--muted); font-size: .78rem; margin-top: 4px; }
  input[type=file] { display: none; }

  /* ---------- Upload queue ---------- */
  .queue { margin-top: 14px; display: flex; flex-direction: column; gap: 9px; }
  .q-item { background: var(--raised); border: 1px solid var(--border);
    border-radius: 12px; padding: 11px 13px; }
  .q-top { display: flex; align-items: center; gap: 9px; min-width: 0; }
  .q-ic { font-size: 1.05rem; flex-shrink: 0; }
  .q-name { font-size: .84rem; font-weight: 600; flex: 1; min-width: 0;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .q-pct { font-size: .76rem; color: var(--sub); font-variant-numeric: tabular-nums; flex-shrink: 0; }
  .q-track { height: 6px; border-radius: 999px; background: rgba(120,150,210,.18);
    overflow: hidden; margin-top: 9px; }
  .q-bar { height: 100%; width: 0%; border-radius: 999px;
    background: linear-gradient(90deg, var(--accent), var(--accent-2)); transition: width .18s ease; }
  .q-bar.ok { background: var(--ok); }
  .q-bar.err { background: var(--danger); }
  .q-meta { font-size: .72rem; color: var(--muted); margin-top: 6px; }

  /* ---------- File list ---------- */
  .files { list-style: none; display: flex; flex-direction: column; }
  .f-item { display: flex; align-items: center; gap: 11px; padding: 12px 4px;
    border-bottom: 1px solid var(--border); }
  .f-item:last-child { border-bottom: none; }
  .f-ic { font-size: 1.4rem; flex-shrink: 0; width: 30px; text-align: center; }
  .f-info { flex: 1; min-width: 0; }
  .f-name { font-size: .88rem; font-weight: 600; word-break: break-word; }
  .f-size { font-size: .72rem; color: var(--muted); margin-top: 2px; }
  .f-actions { display: flex; gap: 7px; flex-shrink: 0; }
  .empty { text-align: center; color: var(--muted); padding: 30px 12px; font-size: .86rem; }
  .empty .ic { font-size: 1.8rem; display: block; margin-bottom: 8px; opacity: .7; }

  .list-head { display: flex; align-items: center; justify-content: space-between; }
  .count { font-size: .72rem; color: var(--muted); font-weight: 600; }

  /* ---------- Toast ---------- */
  .toast-wrap { position: fixed; left: 0; right: 0; bottom: calc(20px + env(safe-area-inset-bottom));
    display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 60; pointer-events: none; }
  .toast { pointer-events: auto; background: var(--surface-solid); border: 1px solid var(--border);
    color: var(--text); padding: 12px 18px; border-radius: 13px; font-size: .86rem; font-weight: 500;
    box-shadow: var(--shadow); display: flex; align-items: center; gap: 9px;
    transform: translateY(14px); opacity: 0; transition: .28s; max-width: min(92vw, 440px); }
  .toast.show { transform: none; opacity: 1; }
  .toast.ok { border-color: rgba(52,211,153,.5); }
  .toast.err { border-color: rgba(248,113,113,.5); }

  footer { text-align: center; color: var(--muted); font-size: .74rem; padding: 8px 16px 4px; }

  @media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
</head>
<body>

<header>
  <div class="head-inner">
    <div class="mark">⚡</div>
    <div class="titles">
      <h1>SimpleShare</h1>
      <p>Local network file transfer</p>
    </div>
    <div class="head-spacer"></div>
    <div class="conn-pill"><span class="conn-dot"></span><span id="conn-text">Connected</span></div>
  </div>
</header>

<div class="wrap">

  <!-- Connect -->
  <div class="card">
    <h2>📡 Share this address with other devices</h2>
    <div class="url-row">
      <div class="url-box" id="server-url">—</div>
      <button class="btn" onclick="copyURL()" id="copy-btn">Copy link</button>
    </div>
    <p class="hint">On another phone or laptop connected to the <strong>same Wi-Fi</strong>, open a browser and type the address above. Then drag files in or tap to download.</p>
  </div>

  <div class="grid">
    <!-- Send -->
    <div class="card">
      <h2>⬆️ Send files</h2>
      <label class="drop" id="drop" for="file-input">
        <div class="ic">📂</div>
        <div class="big">Drop files here or <strong>tap to choose</strong></div>
        <div class="sm">Any type · any size · multiple at once</div>
      </label>
      <input type="file" id="file-input" multiple>
      <div class="queue" id="queue"></div>
    </div>

    <!-- Receive -->
    <div class="card">
      <div class="list-head" style="margin-bottom:14px;">
        <h2 style="margin:0;">⬇️ Available files</h2>
        <span class="count" id="count"></span>
      </div>
      <div id="file-box">
        <div class="empty"><span class="ic">🗂️</span>No files yet</div>
      </div>
      <div style="margin-top:14px; display:flex; gap:8px;">
        <button class="btn btn-ghost btn-sm" onclick="loadFiles()">🔄 Refresh</button>
      </div>
    </div>
  </div>

</div>

<footer>No internet used · files stay on your network · press Ctrl+C in the terminal to stop</footer>

<div class="toast-wrap" id="toast-wrap"></div>

<script>
// ── Connection URL ──────────────────────────────────────────────────────────
const urlBox = document.getElementById('server-url');
urlBox.textContent = window.location.href.replace(/\/$/, '');

function copyURL() {
  const text = urlBox.textContent;
  const done = () => { const b = document.getElementById('copy-btn'); b.textContent = '✓ Copied'; setTimeout(() => b.textContent = 'Copy link', 1600); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done));
  } else { fallbackCopy(text, done); }
}
function fallbackCopy(text, cb) {
  const t = document.createElement('textarea'); t.value = text; document.body.appendChild(t);
  t.select(); try { document.execCommand('copy'); cb(); } catch (e) {} document.body.removeChild(t);
}

// ── Toasts ──────────────────────────────────────────────────────────────────
function toast(msg, kind) {
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || '');
  el.innerHTML = (kind === 'ok' ? '✅ ' : kind === 'err' ? '⚠️ ' : '') + escHtml(msg);
  document.getElementById('toast-wrap').appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 3400);
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function fmt(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  if (b < 1073741824) return (b/1048576).toFixed(1) + ' MB';
  return (b/1073741824).toFixed(2) + ' GB';
}
function escHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
function icon(name) {
  const ext = (name.split('.').pop() || '').toLowerCase();
  return { pdf:'📄', doc:'📝', docx:'📝', txt:'📋', md:'📋', rtf:'📝',
    xls:'📊', xlsx:'📊', csv:'📊', ppt:'📊', pptx:'📊',
    jpg:'🖼️', jpeg:'🖼️', png:'🖼️', gif:'🖼️', webp:'🖼️', svg:'🖼️', heic:'🖼️', bmp:'🖼️',
    mp4:'🎬', mov:'🎬', avi:'🎬', mkv:'🎬', webm:'🎬',
    mp3:'🎵', wav:'🎵', flac:'🎵', ogg:'🎵', m4a:'🎵',
    zip:'🗜️', tar:'🗜️', gz:'🗜️', '7z':'🗜️', rar:'🗜️',
    py:'🐍', js:'📜', ts:'📜', html:'🌐', css:'🎨', json:'🔧',
    sh:'⚙️', bat:'⚙️', exe:'⚙️', apk:'📱', dmg:'💿', iso:'💿' }[ext] || '📁';
}

// ── Upload (sequential, per-file progress) ──────────────────────────────────
const drop = document.getElementById('drop');
const fileInput = document.getElementById('file-input');
const queue = document.getElementById('queue');

drop.addEventListener('dragover',  e => { e.preventDefault(); drop.classList.add('over'); });
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('over'); enqueue(e.dataTransfer.files); });
fileInput.addEventListener('change', () => { enqueue(fileInput.files); fileInput.value = ''; });

let uploading = false;
const pending = [];

function enqueue(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  for (const f of files) pending.push(f);
  if (!uploading) processQueue();
}

async function processQueue() {
  uploading = true;
  while (pending.length) {
    const file = pending.shift();
    await uploadOne(file);
  }
  uploading = false;
  loadFiles();
}

function uploadOne(file) {
  return new Promise(resolve => {
    const row = document.createElement('div');
    row.className = 'q-item';
    row.innerHTML =
      `<div class="q-top">
         <span class="q-ic">${icon(file.name)}</span>
         <span class="q-name">${escHtml(file.name)}</span>
         <span class="q-pct">0%</span>
       </div>
       <div class="q-track"><div class="q-bar"></div></div>
       <div class="q-meta">${fmt(file.size)}</div>`;
    queue.prepend(row);
    const bar = row.querySelector('.q-bar');
    const pct = row.querySelector('.q-pct');
    const meta = row.querySelector('.q-meta');

    const fd = new FormData();
    fd.append('files', file, file.name);

    const xhr = new XMLHttpRequest();
    const started = Date.now();
    xhr.open('POST', '/upload');
    xhr.upload.onprogress = e => {
      if (!e.lengthComputable) return;
      const p = e.loaded / e.total * 100;
      bar.style.width = p + '%';
      pct.textContent = Math.round(p) + '%';
      const secs = (Date.now() - started) / 1000;
      if (secs > 0.3) meta.textContent = `${fmt(file.size)} · ${fmt(e.loaded/secs)}/s`;
    };
    xhr.onload = () => {
      if (xhr.status === 200) {
        bar.style.width = '100%'; bar.classList.add('ok');
        pct.textContent = 'Done'; meta.textContent = fmt(file.size) + ' · sent';
        setTimeout(() => { row.style.transition = 'opacity .4s'; row.style.opacity = '.55'; }, 1200);
      } else {
        bar.classList.add('err'); pct.textContent = 'Failed';
        meta.textContent = 'Upload failed (HTTP ' + xhr.status + ')';
        toast(file.name + ' failed to upload', 'err');
      }
      resolve();
    };
    xhr.onerror = () => { bar.classList.add('err'); pct.textContent = 'Error';
      meta.textContent = 'Network error'; toast('Network error uploading ' + file.name, 'err'); resolve(); };
    xhr.send(fd);
  });
}

// ── Available files ─────────────────────────────────────────────────────────
async function loadFiles() {
  const box = document.getElementById('file-box');
  const count = document.getElementById('count');
  try {
    const res = await fetch('/files');
    const files = await res.json();
    count.textContent = files.length ? files.length + (files.length === 1 ? ' file' : ' files') : '';
    if (!files.length) { box.innerHTML = '<div class="empty"><span class="ic">🗂️</span>No files yet</div>'; return; }
    box.innerHTML = '<ul class="files">' + files.map(f => `
      <li class="f-item">
        <span class="f-ic">${icon(f.name)}</span>
        <div class="f-info">
          <div class="f-name">${escHtml(f.name)}</div>
          <div class="f-size">${fmt(f.size)}</div>
        </div>
        <div class="f-actions">
          <a class="btn btn-sm" href="/download/${encodeURIComponent(f.name)}" download title="Download">⬇️</a>
          <button class="btn btn-ghost btn-icon btn-danger" onclick="deleteFile(${JSON.stringify(f.name).replace(/"/g,'&quot;')}, this)" title="Delete">🗑️</button>
        </div>
      </li>`).join('') + '</ul>';
  } catch (e) {
    box.innerHTML = '<div class="empty" style="color:var(--danger)">Could not load files</div>';
  }
}

async function deleteFile(name, btn) {
  if (!confirm('Delete "' + name + '"?')) return;
  btn.disabled = true;
  try {
    const resp = await fetch('/delete/' + encodeURIComponent(name), { method: 'DELETE' });
    if (resp.ok) { toast('Deleted ' + name, 'ok'); loadFiles(); }
    else { const e = await resp.json().catch(() => ({})); toast('Could not delete: ' + (e.error || resp.statusText), 'err'); btn.disabled = false; }
  } catch (e) { toast('Network error while deleting', 'err'); btn.disabled = false; }
}

loadFiles();
setInterval(loadFiles, 5000);
</script>
</body>
</html>"""

# ─── Streaming multipart parser ───────────────────────────────────────────────

_FILENAME_RE = re.compile(r'filename\*?=(?:"([^"]*)"|([^;\r\n]*))', re.IGNORECASE)


class _NullSink:
    """A writable sink that discards everything (for non-file form fields)."""
    def write(self, data):
        return len(data)


class MultipartStreamParser:
    """
    Incrementally parse a multipart/form-data body from a file-like `rfile`,
    writing each uploaded file straight to disk in chunks. Never loads a whole
    file into memory, so arbitrarily large uploads work.
    """

    def __init__(self, rfile, boundary, content_length, save_dir, unique_name):
        self.rfile = rfile
        self.boundary = boundary if isinstance(boundary, bytes) else boundary.encode()
        self.remaining = content_length
        self.save_dir = save_dir
        self.unique_name = unique_name
        self.buf = b""

    def _pull(self):
        """Read one chunk from the wire into the buffer. Returns bytes read."""
        if self.remaining <= 0:
            return 0
        data = self.rfile.read(min(CHUNK, self.remaining))
        if not data:
            self.remaining = 0
            return 0
        self.remaining -= len(data)
        self.buf += data
        return len(data)

    def _readline(self):
        """Read a single CRLF-terminated line (without the CRLF)."""
        while b"\r\n" not in self.buf:
            if self._pull() == 0:
                line, self.buf = self.buf, b""
                return line
        idx = self.buf.find(b"\r\n")
        line = self.buf[:idx]
        self.buf = self.buf[idx + 2:]
        return line

    def _stream_body(self, out):
        """Write part content to `out` until the next boundary delimiter."""
        marker = b"\r\n--" + self.boundary
        keep = len(marker) - 1
        while True:
            idx = self.buf.find(marker)
            if idx != -1:
                out.write(self.buf[:idx])
                # Leave "--boundary..." in the buffer (drop the leading CRLF).
                self.buf = self.buf[idx + 2:]
                return
            if self.remaining <= 0:
                out.write(self.buf)
                self.buf = b""
                return
            if len(self.buf) > keep:
                out.write(self.buf[:-keep])
                self.buf = self.buf[-keep:]
            self._pull()

    def parse(self):
        """Parse the whole body; return the list of saved filenames."""
        saved = []
        delim = b"--" + self.boundary
        line = self._readline()  # first boundary line (preamble is normally empty)

        while True:
            if line.startswith(delim) and line[len(delim):] == b"--":
                break  # closing boundary
            if line != delim:
                # Not at a boundary yet (stray preamble). Advance, or stop at EOF.
                if self.remaining <= 0 and not self.buf:
                    break
                line = self._readline()
                continue

            # Read part headers until a blank line.
            filename = None
            while True:
                header = self._readline()
                if header == b"":
                    break
                text = header.decode("utf-8", "ignore")
                if text.lower().startswith("content-disposition"):
                    m = _FILENAME_RE.search(text)
                    if m:
                        filename = (m.group(1) or m.group(2) or "").strip()

            if filename:
                safe = self.unique_name(Path(filename).name)
                path = self.save_dir / safe
                with open(path, "wb") as out:
                    self._stream_body(out)
                # A browser that only opened the file picker but sent an empty
                # filename won't reach here; guard against 0-byte accidental parts.
                if path.stat().st_size == 0 and not filename:
                    path.unlink(missing_ok=True)
                else:
                    saved.append(safe)
            else:
                self._stream_body(_NullSink())

            line = self._readline()  # boundary line that _stream_body left behind

        return saved


# ─── HTTP Request Handler ─────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        try:
            print(f"  [{self.address_string()}] {args[0]}")
        except Exception:
            pass

    # ── GET ──
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", HTML.encode())
        elif path == "/files":
            self._send(200, "application/json", json.dumps(self._list_files()).encode())
        elif path.startswith("/download/"):
            self._serve_file(unquote(path[len("/download/"):]))
        else:
            self.send_error(404, "Not found")

    # ── POST (upload) ──
    def do_POST(self):
        if urlparse(self.path).path != "/upload":
            self.send_error(404)
            return
        ct = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ct or "boundary=" not in ct:
            self._send(400, "application/json", json.dumps({"error": "Expected multipart/form-data"}).encode())
            return
        length = int(self.headers.get("Content-Length", 0))
        boundary = ct.split("boundary=", 1)[1].strip().strip('"')

        share_dir = self.server.share_dir
        share_dir.mkdir(parents=True, exist_ok=True)

        try:
            parser = MultipartStreamParser(
                self.rfile, boundary, length, share_dir, self._unique_name
            )
            saved = parser.parse()
            for name in saved:
                size = (share_dir / name).stat().st_size
                print(f"  📥 Received: {name}  ({size:,} bytes)")
            self._send(200, "application/json", json.dumps({"saved": len(saved), "files": saved}).encode())
        except Exception as exc:
            print(f"  ⚠️  Upload error: {exc}")
            self._send(500, "application/json", json.dumps({"error": str(exc)}).encode())

    # ── DELETE ──
    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/delete/"):
            self.send_error(404, "Not found")
            return
        safe_name = Path(unquote(path[len("/delete/"):])).name
        file_path = self.server.share_dir / safe_name
        if not file_path.exists() or not file_path.is_file():
            self._send(404, "application/json", json.dumps({"error": "File not found"}).encode())
            return
        try:
            file_path.unlink()
            print(f"  🗑️  Deleted: {safe_name}")
            self._send(200, "application/json", json.dumps({"deleted": True}).encode())
        except Exception as exc:
            self._send(500, "application/json", json.dumps({"error": str(exc)}).encode())

    # ── Helpers ──
    def _send(self, code, ct, body):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _unique_name(self, name):
        """Return a filename that doesn't collide with an existing one."""
        name = name or "file"
        target = self.server.share_dir / name
        if not target.exists():
            return name
        stem = Path(name).stem
        suffix = Path(name).suffix
        i = 1
        while True:
            candidate = f"{stem} ({i}){suffix}"
            if not (self.server.share_dir / candidate).exists():
                return candidate
            i += 1

    def _list_files(self):
        share_dir = self.server.share_dir
        if not share_dir.exists():
            return []
        return [
            {"name": f.name, "size": f.stat().st_size}
            for f in sorted(share_dir.iterdir(), key=lambda p: p.name.lower())
            if f.is_file()
        ]

    def _serve_file(self, filename):
        share_dir = self.server.share_dir
        filename = Path(filename).name
        filepath = share_dir / filename
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404, "File not found")
            return
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        size = filepath.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "none")
        self.end_headers()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(CHUNK):
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


# ─── Utilities ────────────────────────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_banner(ip, port, share_dir):
    url = f"http://{ip}:{port}"
    print(f"""
╔══════════════════════════════════════════╗
║           ⚡  SimpleShare                 ║
║      Local Network File Transfer          ║
╚══════════════════════════════════════════╝

  🌐  Open in any browser on this network:

        {url}

  📁  Shared folder : {share_dir.resolve()}
  🖥️   Also works at : http://localhost:{port}

  → Other devices must be on the same Wi-Fi
    or LAN. Press Ctrl+C to stop.
──────────────────────────────────────────────
""")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SimpleShare — local network P2P file transfer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python simpleshare.py --port 9000 --dir ~/Desktop/share",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--dir", type=str, default=DEFAULT_DIR,
                        help=f"Folder to share from/to (default: {DEFAULT_DIR})")
    args = parser.parse_args()

    share_dir = Path(args.dir).expanduser().resolve()
    share_dir.mkdir(parents=True, exist_ok=True)

    ip = get_local_ip()
    print_banner(ip, args.port, share_dir)

    try:
        server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    except OSError as exc:
        print(f"  ❌  Could not start on port {args.port}: {exc}")
        print(f"      Try another port, e.g.  python simpleshare.py --port 9090")
        sys.exit(1)

    server.share_dir = share_dir
    server.daemon_threads = True

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋  Stopped. Files saved in:", share_dir, "\n")
        server.server_close()


if __name__ == "__main__":
    main()
