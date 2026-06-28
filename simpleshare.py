#!/usr/bin/env python3
"""
SimpleShare — Local Network File Transfer
No internet. No accounts. Just share files.
Now with delete support, fixed file downloads, and
correct file naming (overwrites, no auto-rename).
"""

import os
import sys
import socket
import json
import mimetypes
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote, urlparse

# ─── Configuration ────────────────────────────────────────────────────────────

DEFAULT_PORT = 8080
DEFAULT_DIR  = "shared_files"

# ─── Embedded Web UI (delete buttons included) ───────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SimpleShare</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f172a; --surface: #1e293b; --border: #334155;
    --accent: #38bdf8; --text: #e2e8f0; --muted: #64748b; --sub: #94a3b8;
    --danger: #f87171;
  }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh; }
  header { background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 18px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 1.25rem; color: var(--accent); }
  header p  { font-size: 0.8rem; color: var(--sub); margin-top: 2px; }
  .wrap { max-width: 860px; margin: 0 auto; padding: 28px 20px; }
  .card { background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 22px; margin-bottom: 20px; }
  .card h2 { font-size: 0.9rem; font-weight: 600; color: var(--sub);
    text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px; }
  .url-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .url-box { flex: 1; background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; font-family: monospace; font-size: 0.9rem;
    color: var(--accent); word-break: break-all; }
  .btn { background: var(--accent); color: #0f172a; border: none;
    padding: 10px 20px; border-radius: 8px; font-weight: 700; cursor: pointer;
    font-size: 0.85rem; transition: opacity .15s; white-space: nowrap; }
  .btn:hover { opacity: .85; }
  .btn:disabled { opacity: .4; cursor: default; }
  .btn-sm { padding: 7px 14px; font-size: 0.78rem; }
  .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text); }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
  .btn-danger { color: var(--danger); border-color: var(--danger); }
  .btn-danger:hover { background: var(--danger); color: #fff; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
  .drop-zone { border: 2px dashed var(--border); border-radius: 10px;
    padding: 36px 20px; text-align: center; cursor: pointer; transition: all .2s; }
  .drop-zone:hover, .drop-zone.over { border-color: var(--accent);
    background: rgba(56,189,248,.06); }
  .drop-zone .icon { font-size: 2rem; margin-bottom: 10px; }
  .drop-zone p { color: var(--muted); font-size: 0.875rem; }
  .drop-zone strong { color: var(--accent); }
  input[type=file] { display: none; }
  .prog-wrap { margin-top: 12px; display: none; }
  .prog-track { background: var(--border); border-radius: 4px; height: 6px; overflow: hidden; }
  .prog-bar   { background: var(--accent); height: 100%; border-radius: 4px;
    transition: width .25s; width: 0%; }
  .msg { margin-top: 10px; font-size: 0.85rem; min-height: 1.2em; }
  .msg.ok  { color: #4ade80; }
  .msg.err { color: #f87171; }
  .msg.inf { color: var(--accent); }
  .file-list { list-style: none; }
  .file-item { display: flex; align-items: center; justify-content: space-between;
    padding: 11px 0; border-bottom: 1px solid var(--border); gap: 10px; }
  .file-item:last-child { border-bottom: none; }
  .file-meta { display: flex; align-items: center; gap: 10px; min-width: 0; }
  .file-icon { font-size: 1.25rem; flex-shrink: 0; }
  .file-name { font-size: 0.875rem; word-break: break-all; }
  .file-size { font-size: 0.73rem; color: var(--muted); margin-top: 1px; }
  .empty { text-align: center; color: var(--muted); padding: 24px; font-size: 0.875rem; }
  .copied { animation: flash .5s; }
  @keyframes flash { 0%,100%{ opacity:1 } 50%{ opacity:.4 } }
</style>
</head>
<body>
<header>
  <div>
    <h1>⚡ SimpleShare</h1>
    <p>Local network file transfer — no internet required</p>
  </div>
</header>

<div class="wrap">

  <!-- Connect URL -->
  <div class="card">
    <h2>📡 Share this address with other devices</h2>
    <div class="url-row">
      <div class="url-box" id="server-url">—</div>
      <button class="btn btn-sm btn-ghost" onclick="copyURL()" id="copy-btn">Copy</button>
    </div>
  </div>

  <!-- Upload + Download -->
  <div class="grid">
    <div class="card">
      <h2>⬆️ Send Files</h2>
      <div class="drop-zone" id="drop-zone">
        <div class="icon">📂</div>
        <p>Drag &amp; drop files here<br>or <strong>click to browse</strong></p>
      </div>
      <input type="file" id="file-input" multiple>
      <div class="prog-wrap" id="prog-wrap">
        <div class="prog-track"><div class="prog-bar" id="prog-bar"></div></div>
      </div>
      <div class="msg" id="msg"></div>
    </div>

    <div class="card">
      <h2>⬇️ Available Files</h2>
      <div id="file-box"><div class="empty">No files yet</div></div>
      <div style="margin-top:14px">
        <button class="btn btn-sm btn-ghost" onclick="loadFiles()">🔄 Refresh</button>
      </div>
    </div>
  </div>

</div>

<script>
// ── URL display ───────────────────────────────────────────────────────────────
const urlBox = document.getElementById('server-url');
urlBox.textContent = window.location.href.replace(/\/$/, '');

function copyURL() {
  navigator.clipboard.writeText(urlBox.textContent);
  const btn = document.getElementById('copy-btn');
  btn.textContent = '✓ Copied';
  btn.classList.add('copied');
  setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1600);
}

// ── Upload ────────────────────────────────────────────────────────────────────
const dropZone  = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const progWrap  = document.getElementById('prog-wrap');
const progBar   = document.getElementById('prog-bar');
const msg       = document.getElementById('msg');

dropZone.addEventListener('click',      () => fileInput.click());
dropZone.addEventListener('dragover',   e  => { e.preventDefault(); dropZone.classList.add('over'); });
dropZone.addEventListener('dragleave',  ()  => dropZone.classList.remove('over'));
dropZone.addEventListener('drop',       e  => { e.preventDefault(); dropZone.classList.remove('over'); upload(e.dataTransfer.files); });
fileInput.addEventListener('change',   ()  => upload(fileInput.files));

function setMsg(text, type) {
  msg.textContent = text;
  msg.className   = 'msg ' + (type || '');
}

function upload(files) {
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append('files', f);

  progWrap.style.display = 'block';
  progBar.style.width    = '0%';
  setMsg('Uploading…', 'inf');

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload');
  xhr.upload.onprogress = e => {
    if (e.lengthComputable) progBar.style.width = (e.loaded / e.total * 100) + '%';
  };
  xhr.onload = () => {
    progBar.style.width = '100%';
    if (xhr.status === 200) {
      const r = JSON.parse(xhr.responseText);
      setMsg('✅ ' + r.saved + ' file(s) uploaded!', 'ok');
      fileInput.value = '';
      loadFiles();
    } else {
      setMsg('❌ Upload failed (HTTP ' + xhr.status + ')', 'err');
    }
  };
  xhr.onerror = () => setMsg('❌ Network error', 'err');
  xhr.send(fd);
}

// ── Delete file ───────────────────────────────────────────────────────────────
async function deleteFile(filename, button) {
  if (!confirm(`Delete "${filename}"?`)) return;
  button.disabled = true;
  try {
    const resp = await fetch('/delete/' + encodeURIComponent(filename), { method: 'DELETE' });
    if (resp.ok) {
      loadFiles();
    } else {
      const err = await resp.json();
      alert('Failed to delete: ' + (err.error || resp.statusText));
    }
  } catch (e) {
    alert('Network error while deleting.');
  } finally {
    button.disabled = false;
  }
}

// ── File list ─────────────────────────────────────────────────────────────────
function fmt(b) {
  if (b < 1024)           return b + ' B';
  if (b < 1048576)        return (b/1024).toFixed(1)    + ' KB';
  if (b < 1073741824)     return (b/1048576).toFixed(1) + ' MB';
  return                         (b/1073741824).toFixed(2) + ' GB';
}

function icon(name) {
  const ext = name.split('.').pop().toLowerCase();
  return {
    pdf:'📄', doc:'📝', docx:'📝', txt:'📋', md:'📋',
    xls:'📊', xlsx:'📊', csv:'📊',
    jpg:'🖼️', jpeg:'🖼️', png:'🖼️', gif:'🖼️', webp:'🖼️', svg:'🖼️',
    mp4:'🎬', mov:'🎬', avi:'🎬', mkv:'🎬',
    mp3:'🎵', wav:'🎵', flac:'🎵', ogg:'🎵',
    zip:'🗜️', tar:'🗜️', gz:'🗜️', '7z':'🗜️', rar:'🗜️',
    py:'🐍', js:'📜', ts:'📜', html:'🌐', css:'🎨', json:'🔧',
    sh:'⚙️', bat:'⚙️', exe:'⚙️', dmg:'💿', pkg:'💿',
  }[ext] || '📁';
}

async function loadFiles() {
  const box = document.getElementById('file-box');
  try {
    const res   = await fetch('/files');
    const files = await res.json();
    if (!files.length) { box.innerHTML = '<div class="empty">No files yet</div>'; return; }
    box.innerHTML = '<ul class="file-list">' + files.map(f => `
      <li class="file-item">
        <div class="file-meta">
          <span class="file-icon">${icon(f.name)}</span>
          <div>
            <div class="file-name">${escHtml(f.name)}</div>
            <div class="file-size">${fmt(f.size)}</div>
          </div>
        </div>
        <div style="display:flex; gap:8px;">
          <a href="/download/${encodeURIComponent(f.name)}" class="btn btn-sm">⬇️</a>
          <button class="btn btn-sm btn-ghost btn-danger" onclick="deleteFile('${escHtml(f.name).replace(/'/g, "\\'")}', this)" title="Remove file">🗑️</button>
        </div>
      </li>`).join('') + '</ul>';
  } catch (e) {
    box.innerHTML = '<div class="empty" style="color:#f87171">Could not load files</div>';
  }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

loadFiles();
setInterval(loadFiles, 4000);
</script>
</body>
</html>"""

# ─── HTTP Request Handler ─────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  [{self.address_string()}] {args[0]} {args[1]}")

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ('/', '/index.html'):
            self._send(200, 'text/html; charset=utf-8', HTML.encode())

        elif path == '/files':
            files = self._list_files()
            self._send(200, 'application/json', json.dumps(files).encode())

        elif path.startswith('/download/'):
            self._serve_file(unquote(path[len('/download/'):]))

        else:
            self.send_error(404, "Not found")

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404)
            return

        ct = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in ct:
            self.send_error(400, "Expected multipart/form-data")
            return

        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)

        boundary = ct.split('boundary=')[-1].strip().encode()
        saved = self._parse_multipart_safe(body, boundary)

        self._send(200, 'application/json', json.dumps({'saved': saved}).encode())

    # ── DELETE ────────────────────────────────────────────────────────────────

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith('/delete/'):
            self.send_error(404, "Not found")
            return

        filename = unquote(path[len('/delete/'):])
        safe_name = Path(filename).name
        share_dir = self.server.share_dir
        file_path = share_dir / safe_name

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return

        try:
            file_path.unlink()
            print(f"  🗑️  Deleted: {safe_name}")
            self._send(200, 'application/json', json.dumps({"deleted": True}).encode())
        except Exception as e:
            self.send_error(500, f"Could not delete: {str(e)}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _send(self, code, ct, body):
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _list_files(self):
        share_dir = self.server.share_dir
        if not share_dir.exists():
            return []
        return [
            {'name': f.name, 'size': f.stat().st_size}
            for f in sorted(share_dir.iterdir())
            if f.is_file()
        ]

    def _serve_file(self, filename):
        share_dir = self.server.share_dir
        filename  = Path(filename).name
        filepath  = share_dir / filename

        if not filepath.exists() or not filepath.is_file():
            self.send_error(404, "File not found")
            return

        mime, _ = mimetypes.guess_type(filename)
        mime     = mime or 'application/octet-stream'
        size     = filepath.stat().st_size

        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', str(size))
        self.end_headers()

        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ── SAFE multipart parser (no rstrip, correct boundary handling) ──────────

    def _parse_multipart_safe(self, body, boundary):
        """Correctly parse multipart/form-data, leaving file content intact.
           Files are saved with their original name, overwriting if it exists.
        """
        share_dir = self.server.share_dir
        share_dir.mkdir(parents=True, exist_ok=True)
        count = 0

        # Split on full boundary marker: \r\n--boundary
        sep = b'\r\n--' + boundary
        # First part before the first boundary is the preamble, ignore it
        parts = body.split(sep)[1:]  # skip preamble

        for part in parts:
            # The part may start with '--' (last boundary) and then be empty
            if part.startswith(b'--'):
                # This is the closing boundary, stop processing
                break

            # Each part: headers\r\n\r\ndata
            # But there may be a trailing \r\n before the next boundary that belongs to the boundary, not the data.
            # According to RFC 2046, the boundary is preceded by \r\n, and the part data does NOT include that \r\n.
            # The split above consumed the \r\n before the boundary, so the part data ends right before the next sep.
            # However, the last part may have an extra '--' at the end (but we already break if part starts with '--').
            # So we just need to separate headers from data.

            # Find the double CRLF
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue  # malformed part

            headers_block = part[:header_end]
            data = part[header_end + 4:]   # skip the \r\n\r\n

            # Decode headers to extract filename
            headers_text = headers_block.decode('utf-8', errors='ignore')
            if 'filename=' not in headers_text:
                continue

            fname = ''
            for piece in headers_text.split(';'):
                piece = piece.strip()
                if piece.startswith('filename='):
                    fname = piece[9:].strip().strip('"').strip("'")
                    break

            if not fname or not data:
                continue

            # Sanitize filename (remove any path)
            fname = Path(fname).name
            out_path = share_dir / fname

            # Overwrite existing file – keeps the original name
            with open(out_path, 'wb') as fh:
                fh.write(data)

            print(f"  📥 Saved: {fname}  ({len(data):,} bytes)")
            count += 1

        return count

# ─── Utilities ────────────────────────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def print_banner(ip, port, share_dir):
    url = f"http://{ip}:{port}"
    print(f"""
╔══════════════════════════════════════════╗
║           ⚡  SimpleShare                ║
║      Local Network File Transfer         ║
╚══════════════════════════════════════════╝

  🌐  Open in any browser on this network:

        {url}

  📁  Shared folder : {share_dir.resolve()}
  🖥️   Also works at: http://localhost:{port}

  → Other devices must be on the same Wi-Fi
    or LAN.  Press Ctrl+C to stop.
──────────────────────────────────────────
""")

# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='SimpleShare — local network P2P file transfer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python simpleshare.py --port 9000 --dir ~/Desktop/share"
    )
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to listen on (default: {DEFAULT_PORT})')
    parser.add_argument('--dir',  type=str, default=DEFAULT_DIR,
                        help=f'Folder to share from/to (default: {DEFAULT_DIR})')
    args = parser.parse_args()

    share_dir = Path(args.dir).expanduser().resolve()
    share_dir.mkdir(parents=True, exist_ok=True)

    ip = get_local_ip()
    print_banner(ip, args.port, share_dir)

    server = HTTPServer(('0.0.0.0', args.port), Handler)
    server.share_dir = share_dir

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  👋  Stopped. Files saved in:", share_dir, "\n")
        server.server_close()

if __name__ == '__main__':
    main()