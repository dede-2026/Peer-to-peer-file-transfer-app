# ⚡ Peer to peer file transfer app

**Dead-simple local network file transfer. No internet. No accounts. No installs beyond Python.**

Send any file — photos, videos, documents, archives — between any devices on the same Wi-Fi or LAN, using just a web browser.

---

## ✨ Features

- 📤 Drag-and-drop **upload** from any device
- 📥 One-click **download** to any device  
- 🌐 Works in **any browser** (Chrome, Safari, Firefox, Edge…)
- 📱 Mobile-friendly — works from phones & tablets
- 🗂️ Supports **any file type**, any size
- ⚙️ Zero dependencies — pure Python standard library
- 🔒 Local-only — traffic never leaves your network

---

## 🚀 Quick Start

### Windows

```
Double-click  run.bat
```

### macOS / Linux

```bash
chmod +x run.sh
./run.sh
```

### Any OS (manual)

```bash
python3 simpleshare.py
```

Then open the printed URL in your browser.  
Share that URL with other devices on the same network.

---

## 📋 Requirements

- **Python 3.7 or newer** — that's it.
- No pip installs. No virtual environments. No Node.js. Nothing.

---

## ⚙️ Options

```
python3 simpleshare.py --port 9000 --dir ~/Desktop/transfers
```

| Flag     | Default         | Description                        |
|----------|-----------------|------------------------------------|
| `--port` | `8080`          | Port the server listens on         |
| `--dir`  | `shared_files/` | Folder where files are stored      |

---

## 📁 How Files Are Stored

Uploaded files land in the `shared_files/` folder (or whatever `--dir` points to).  
Files are **not deleted automatically** — clean up manually when done.  
If you upload a file with the same name twice, it is saved as `name_1.ext`, `name_2.ext`, etc.

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Connection refused" on another device | Make sure both devices are on the same Wi-Fi/LAN |
| Firewall blocking connection | Allow Python / port 8080 through your firewall |
| Port 8080 already in use | Run with `--port 9090` (or any free port) |
| Python not found on Windows | Re-run installer, check "Add Python to PATH" |

See **GUIDE.md** for full installation and cross-platform instructions.

---

## 📜 License

MIT — do whatever you want with it.
