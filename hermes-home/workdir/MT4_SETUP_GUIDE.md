# MT4 on Headless Linux VPS — Full Setup Guide

Goal: Run MetaTrader 4 (Windows app) on a headless Linux server and stream the GUI to a web browser so you can control it like RDP from any device.

## The Stack (5 layers)

```
┌──────────────────────────────────────────────────────┐
│  Browser (anywhere)                                  │
│  ↓ WebSocket                                         │
│  Cloudflare Tunnel (cloudflared)                     │
│  ↓ HTTPS                                             │
│  noVNC + websockify  (port 8080 — web frontend)      │
│  ↓ WebSocket → VNC                                   │
│  x11vnc             (port 5999 — VNC server)         │
│  ↓ X11 framebuffer                                   │
│  Xvfb               (display :99 — virtual monitor) │
│  ↓ X11                                               │
│  Wine 9.0           (Windows compatibility layer)   │
│  ↓ Win32 calls                                       │
│  MetaTrader 4 terminal.exe  (the actual app)         │
└──────────────────────────────────────────────────────┘
```

Each layer is a separate, well-tested Linux tool. All free, all open source.

## Step-by-step

### 1. Install dependencies (one time, ~3 min)
```bash
sudo dpkg --add-architecture i386
sudo apt update -qq
sudo apt install -y -qq wine64 wine32:i386 xvfb x11vnc novnc websockify curl wget
```

**Why both wine64 and wine32:** MT4 setup is 64-bit but downloads/installs 32-bit components. The dual install avoids the "experimental wow64 mode" errors.

### 2. Start the virtual display
```bash
export DISPLAY=:99
export WINEPREFIX=/home/runner/.wine
export WINEARCH=win64         # CRITICAL: must be 64-bit
export WINEDEBUG=-all         # silence wine log spam
Xvfb :99 -screen 0 1280x800x24 -ac
```

Run in background. `-ac` disables X11 access control so x11vnc can connect.

### 3. Initialize wine prefix
```bash
wineboot --init
```

Creates `~/.wine/drive_c/Program Files/`, registry, etc. First run ~30s.

### 4. Download + install MT4
```bash
wget -q "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe" -O /tmp/mt4setup.exe
wine /tmp/mt4setup.exe /auto
```

`/auto` skips the GUI wizard. Installs to `~/.wine/drive_c/Program Files (x86)/MetaTrader 4/`

### 5. Launch MT4
```bash
cd "$WINEPREFIX/drive_c/Program Files (x86)/MetaTrader 4"
wine terminal.exe
```

First launch shows "Open an Account" dialog. Run in background.

### 6. Start VNC server
```bash
x11vnc -display :99 -nopw -forever -shared -xkb -rfbport 5999 -bg -o /tmp/x11vnc.log
```

Flags:
- `-nopw` — no password (single-user VPS)
- `-forever` — keep alive after viewer disconnects
- `-shared` — multiple viewers OK
- `-rfbport 5999` — VNC port
- `-bg` — daemonize

### 7. Start noVNC web frontend
```bash
websockify --web /usr/share/novnc 8080 localhost:5999
```

Port 8080 serves the HTML5 VNC client. WebSocket proxies to x11vnc on 5999.

### 8. Public tunnel
```bash
wget -q -O /tmp/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
chmod +x /tmp/cloudflared
/tmp/cloudflared tunnel --url http://localhost:8080 --no-autoupdate
```

Watch the output for the `https://*.trycloudflare.com` URL. No account, no signup, free.

### 9. Give user the URL
```
https://<random-subdomain>.trycloudflare.com/vnc.html
```

The `/vnc.html` path opens the noVNC HTML5 client. User clicks "Connect" once to start the session.

## Common pitfalls I hit and how to fix

| Problem | Cause | Fix |
|---|---|---|
| `it looks like wine32 is missing` | 32-bit support not installed | `dpkg --add-architecture i386 && apt install wine32:i386` |
| `Bad EXE format for Z:\tmp\mt4setup.exe` | wineprefix is 32-bit but exe is 64-bit | Delete `~/.wine`, set `WINEARCH=win64`, re-init |
| `failed to load ntdll.dll` | 32-bit wineprefix but 64-bit binary | Same as above |
| `Server is already active for display 99` | stale `/tmp/.X99-lock` | `rm /tmp/.X99-lock` then restart Xvfb |
| `x11vnc exits silently` | DISPLAY env var not inherited | Pass `DISPLAY=:99 x11vnc ...` inline, not just `export` |
| ALSA errors in wine log | No sound card on VPS | Harmless, ignore |
| `cat ~/.wine/system.reg` shows `#arch=win32` | Default arch for new prefix | Always set `WINEARCH=win64` before `wineboot` |

## Process checklist
All 5 should be alive:
```bash
ps aux | grep -E "terminal.exe|x11vnc|websockify|Xvfb|cloudflared" | grep -v grep
ss -tlnp | grep -E "5999|8080"
```

## Persistence
Wine prefix + MT4 install survive VPS reboots at `~/.wine/`. The 5 background processes do not. To restore after reboot, just re-run steps 2, 5, 6, 7, 8 (steps 1, 3, 4 are one-time).

## Custom broker setup
Replace the download URL in step 4 with the broker's installer:
- MetaQuotes: `https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe`
- IC Markets: from `https://www.icmarkets.com/tools/mt4-download/`
- Pepperstone: from their portal (login required)
- Exness: from their portal

Then in MT4: `File → Open Account → enter credentials`. Or pick a demo server (MetaQuotes-Demo, ICMarkets-Demo, etc) for $10K play money.

## Adding custom EAs
```bash
cp /path/to/MyEA.ex4 "$WINEPREFIX/drive_c/Program Files (x86)/MetaTrader 4/MQL4/Experts/"
```
In MT4: `Navigator → Expert Advisors → right-click → Refresh`, drag EA onto a chart.

## File locations
- Wine prefix: `~/.wine/`
- MT4 install: `~/.wine/drive_c/Program Files (x86)/MetaTrader 4/`
- Custom EAs: `~/.wine/drive_c/Program Files (x86)/MetaTrader 4/MQL4/Experts/`
- Logs: `~/.wine/drive_c/Program Files (x86)/MetaTrader 4/logs/`
- Saved settings: `~/.wine/drive_c/Program Files (x86)/MetaTrader 4/profiles/`

## Resource usage on a 2-core/15GB VPS
- Wine + MT4: ~200-300MB RAM
- x11vnc: ~50MB
- websockify: ~50MB
- cloudflared: ~30MB
- Xvfb: ~30MB
- **Total: ~400MB RAM, 5-10% CPU idle, 30-50% during backtests**

Plenty of headroom for multiple instances or other workloads.

## Security notes
- `-nopw` on x11vnc means anyone who finds the VNC port has full access. The Cloudflare tunnel hides port 5999 from the public internet, so this is fine.
- The Cloudflare quick tunnel URL is long and random. Not brute-forceable. Treat it as a secret.
- For production, add a VNC password and use a named Cloudflare tunnel with access policies.

## Re-runnable one-liner
```bash
# Resume after reboot / env reset
export DISPLAY=:99 WINEPREFIX=/home/runner/.wine WINEARCH=win64 WINEDEBUG=-all
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1280x800x24 -ac &
sleep 2
cd "$WINEPREFIX/drive_c/Program Files (x86)/MetaTrader 4" && wine terminal.exe &
x11vnc -display :99 -nopw -forever -shared -xkb -rfbport 5999 -bg
websockify --web /usr/share/novnc 8080 localhost:5999 &
/tmp/cloudflared tunnel --url http://localhost:8080 --no-autoupdate
```
