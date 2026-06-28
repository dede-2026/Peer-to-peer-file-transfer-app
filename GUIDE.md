# Peer to peer file transfer app — Complete Guide

Everything you need to install, run, and use Peer to peer file transfer app on Windows, macOS, and Linux.

---

## Table of Contents

1. [How it works](#how-it-works)
2. [Installing Python](#installing-python)
   - [Windows](#windows-python)
   - [macOS](#macos-python)
   - [Linux](#linux-python)
3. [Running Peer to peer file transfer app](#running-Peer to peer file transfer app)
   - [Windows](#windows-run)
   - [macOS](#macos-run)
   - [Linux](#linux-run)
4. [Sharing Files Between Devices](#sharing-files-between-devices)
5. [Common Scenarios](#common-scenarios)
6. [Firewall & Network Notes](#firewall--network-notes)
7. [Command-Line Options](#command-line-options)
8. [Troubleshooting](#troubleshooting)

---

## How it works

Peer to peer file transfer app runs a tiny web server on your machine. Any other device on the **same Wi-Fi or wired LAN** can open the server's address in a browser and:

- **Upload** files to your machine (drag & drop or file picker)
- **Download** files your machine is sharing

No internet connection is used. Nothing is sent to any cloud service.

```
 Your laptop (runs the server)
      │
      │  Wi-Fi / LAN
      ├──────────── Phone (opens browser → uploads photos)
      ├──────────── Tablet
      └──────────── Another laptop (downloads files)
```

---

## Installing Python

Peer to peer file transfer app needs **Python 3.7 or newer**. It uses only the standard library — no pip installs required.

---

### Windows Python

1. Go to **https://www.python.org/downloads/**
2. Click the big **"Download Python 3.x.x"** button
3. Run the installer
4. ✅ **Check the box: "Add Python to PATH"** (very important — at the bottom of the first screen)
5. Click **Install Now**

**Verify it worked** — open Command Prompt (`Win + R` → type `cmd` → Enter):

```
python --version
```

You should see something like `Python 3.12.0`.

> **Windows Store Python:** If you get a Microsoft Store prompt instead of a version number, open **Settings → Apps → App execution aliases** and toggle off the `python.exe` aliases, then reinstall from python.org.

---

### macOS Python

**Option A — Python.org installer (recommended for beginners)**

1. Go to **https://www.python.org/downloads/macos/**
2. Download the latest macOS installer package (.pkg)
3. Open and follow the installer

**Option B — Homebrew (recommended if you use the terminal)**

```bash
# Install Homebrew first (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Then install Python
brew install python
```

**Option C — macOS Ventura+ already has Python 3**

```bash
python3 --version
```

If you see a version ≥ 3.7, you're ready.

---

### Linux Python

Most Linux distros ship with Python 3. Check first:

```bash
python3 --version
```

If not installed:

**Ubuntu / Debian / Raspberry Pi OS:**
```bash
sudo apt update && sudo apt install python3
```

**Fedora / RHEL / CentOS:**
```bash
sudo dnf install python3
```

**Arch Linux:**
```bash
sudo pacman -S python
```

**Alpine:**
```bash
apk add python3
```

---

## Running Peer to peer file transfer app

### Windows Run

**Option 1 — Double-click:**  
Double-click **`run.bat`**. A terminal window opens and shows the server URL.

**Option 2 — Command Prompt:**
```
cd path\to\Peer to peer file transfer app
python Peer to peer file transfer app.py
```

**Option 3 — PowerShell:**
```powershell
cd path\to\Peer to peer file transfer app
python Peer to peer file transfer app.py
```

The server prints something like:
```
  🌐  Open in any browser on this network:
        http://192.168.1.42:8080
```

Open that URL in your browser. You're live.

---

### macOS Run

**Option 1 — Shell script:**
```bash
cd ~/Downloads/Peer to peer file transfer app   # wherever you extracted it
chmod +x run.sh              # only needed once
./run.sh
```

**Option 2 — Direct Python:**
```bash
cd ~/Downloads/Peer to peer file transfer app
python3 Peer to peer file transfer app.py
```

**Allow firewall prompt:** macOS may ask "Do you want to allow incoming network connections?" → click **Allow**.

---

### Linux Run

```bash
cd ~/Peer to peer file transfer app
chmod +x run.sh     # once
./run.sh
```

Or directly:
```bash
python3 Peer to peer file transfer app.py
```

**Running in the background (optional):**
```bash
nohup python3 Peer to peer file transfer app.py &
echo "PID: $!"
```

To stop it: `kill <PID>` or find it with `pkill -f Peer to peer file transfer app.py`.

**Running as a systemd service (optional, for always-on sharing):**

Create `/etc/systemd/system/Peer to peer file transfer app.service`:
```ini
[Unit]
Description=Peer to peer file transfer app File Transfer
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/youruser/Peer to peer file transfer app/Peer to peer file transfer app.py --port 8080
WorkingDirectory=/home/youruser/Peer to peer file transfer app
Restart=on-failure
User=youruser

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable Peer to peer file transfer app
sudo systemctl start Peer to peer file transfer app
```

---

## Sharing Files Between Devices

### Step-by-step

1. **Run Peer to peer file transfer app** on the device that will send or receive files.
2. Note the URL printed in the terminal, e.g. `http://192.168.1.42:8080`
3. On any other device (same Wi-Fi/LAN), open a browser and go to that URL.
4. **To send a file from another device → your machine:** drag and drop the file onto the upload zone.
5. **To download a file from your machine → another device:** click the ⬇️ button next to the file.

### Which device runs the server?

It doesn't matter. Any device can be the server. Files are uploaded to and downloaded from the device running Peer to peer file transfer app.

**Typical setups:**

| Goal | Who runs the server |
|------|-------------------|
| Move photos from phone to laptop | Run on laptop; open URL on phone; upload photos |
| Send a doc from laptop to tablet | Run on laptop; open URL on tablet; download the doc |
| Exchange files between two laptops | Run on either; open URL on the other |
| Share files with multiple people | Run on one machine; everyone opens the URL |

---

## Common Scenarios

### Phone → Laptop (photos, videos)

1. Run Peer to peer file transfer app on your laptop
2. On your phone, open the browser and type the URL
3. Tap the upload zone → pick photos from camera roll
4. They appear in the laptop's `shared_files/` folder instantly

### Laptop → Phone

1. Run Peer to peer file transfer app on your laptop, put the files in `shared_files/`  
   (or upload them via localhost)
2. On your phone, open the URL and tap the ⬇️ button

### Two Laptops (different OS, same network)

Works exactly the same. A Mac and a Windows PC share files seamlessly — neither needs special software beyond a browser.

### Raspberry Pi as always-on file drop

Run Peer to peer file transfer app on a Raspberry Pi with `--dir /mnt/usb` pointing to a USB drive. Any device on the network can upload or grab files any time.

---

## Firewall & Network Notes

### Same Wi-Fi / LAN required

Both devices **must** be on the same network. This means:
- Same home/office Wi-Fi, OR
- Same wired LAN switch

It does **not** work over the internet or across different networks without extra setup (like a VPN or tunneling tool).

### Firewall — Windows

When you first run Peer to peer file transfer app, Windows Firewall may ask for permission. Click **"Allow access"**.

If you missed it:
1. Open **Windows Defender Firewall → Allow an app**
2. Add `python.exe` or allow port 8080

Or via PowerShell (admin):
```powershell
New-NetFirewallRule -DisplayName "Peer to peer file transfer app" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

### Firewall — macOS

macOS prompts when a server first accepts connections. Click **Allow**.

If blocked: **System Settings → Network → Firewall → Options** → add Python.

### Firewall — Linux (UFW)

```bash
sudo ufw allow 8080/tcp
```

### Firewall — Linux (firewalld)

```bash
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

### Phone hotspot

If you're on a phone hotspot, devices connected to the hotspot can reach the server. The hotspot's gateway address is typically shown in your hotspot settings.

---

## Command-Line Options

```
python3 Peer to peer file transfer app.py [--port PORT] [--dir DIRECTORY]
```

| Option | Default | Example |
|--------|---------|---------|
| `--port` | `8080` | `--port 9000` |
| `--dir`  | `shared_files` | `--dir ~/Desktop/share` |

**Examples:**

```bash
# Different port
python3 Peer to peer file transfer app.py --port 9090

# Custom folder
python3 Peer to peer file transfer app.py --dir /mnt/usb/drops

# Both
python3 Peer to peer file transfer app.py --port 8888 --dir ~/Documents/transfer
```

---

## Troubleshooting

### "This site can't be reached" / "Connection refused"

- Are both devices on the **same Wi-Fi / network**?
- Is Peer to peer file transfer app still running (check the terminal)?
- Did you type the **exact IP and port** shown in the terminal?
- Try `http://` (not `https://`) — Peer to peer file transfer app does not use TLS

### Port already in use

```
OSError: [Errno 98] Address already in use
```

Something else is using port 8080. Just pick another:
```bash
python3 Peer to peer file transfer app.py --port 9090
```

### Python not found

- **Windows:** Reinstall Python from python.org, check "Add Python to PATH"
- **macOS:** Use `python3` instead of `python`
- **Linux:** `sudo apt install python3` (or your distro's equivalent)

### Slow upload / download

- Large files are limited by your Wi-Fi speed, not Peer to peer file transfer app
- For faster transfers, connect both devices with an Ethernet cable if possible

### File not appearing after upload

- Click **🔄 Refresh** (or wait 4 seconds — it auto-refreshes)
- Check the `shared_files/` folder directly on the server machine

### macOS "App can't be opened" or Gatekeeper warning

Peer to peer file transfer app is a Python script, not a signed app. If a Gatekeeper warning appears:
- Right-click `run.sh` → Open → Open anyway

Or in Terminal:
```bash
xattr -dr com.apple.quarantine /path/to/Peer to peer file transfer app
```

### "Received" shows 0 bytes

The file may have had zero content, or the browser cancelled mid-transfer. Try again.

---

## Security Notes

- Peer to peer file transfer app has **no authentication**. Anyone on your network can upload or download.
- Use it on **trusted networks** (home, office). Don't run it on public Wi-Fi.
- Stop the server (`Ctrl+C`) when you're done.
- Files stay on disk until you delete them manually.

---

*Peer to peer file transfer app is MIT licensed. Fork it, modify it, make it yours.*
