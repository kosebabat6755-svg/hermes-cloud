---
name: headless-windows-app-streaming
description: Stream a Windows GUI app from a Linux VPS to a browser.
---

# Headless Windows App Streaming (VPS → Browser)

Use when the user wants a Windows GUI application (MetaTrader 4/5, TradingView desktop, Photoshop, AutoCAD, etc.) running on a headless Linux VPS, controlled from any browser, with no RDP/teamviewer and no public IP. Also use for any "run this Windows app as a long-running service on my VPS and let me use it from the web" request.

The 5-layer stack separates concerns: each component is a small, well-tested Linux tool you can swap or replace.

## The 5-layer stack

```
Browser → Cloudflare tunnel → noVNC (websockify) → x11vnc → Xvfb (display) → Wine → Windows .exe
```

- **Xvfb** = fake graphics card + virtual display (no monitor needed). Target display `:99` (MT4) / `:98` (MT5).
- **Wine** = translates Windows API calls (CreateWindow, GDI, etc.) into X11 calls on the fly. So `terminal.exe` runs as a Linux process. Needs 64-bit prefix (`WINEARCH=win64`).
- **x11vnc** = snapshots the Xvfb display on a port (5999) as VNC protocol. Each display gets one port.
- **websockify + noVNC** = bridges browser WebSocket to VNC. Serves the noVNC HTML/JS client on a web port (8080).
- **cloudflared** = outbound TLS tunnel to Cloudflare edge → public `*.trycloudflare.com` URL. No inbound port forwarding needed; works behind NAT/firewall.

## One-time install (Ubuntu/Debian, ~3 min)

```bash
dpkg --add-architecture i386
apt update -qq
apt install -y -qq wine64 wine32:i386 xvfb x11vnc novnc websockify curl wget
# For a public URL without exposing ports:
wget -q -O /tmp/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" && chmod +x /tmp/cloudflared
```

## One-time per app — install + start (manual run, no systemd)

```bash
export DISPLAY=:99 WINEPREFIX=/root/.wine-mt4 WINEARCH=win64 WINEDEBUG=-all

# 1. Virtual display
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1280x800x24 -ac &
sleep 2

# 2. Init wine prefix (only first time)
wineboot --init

# 3. Install Windows app (only first time)
wget -q "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt4/mt4setup.exe" -O /tmp/mt4setup.exe
wine /tmp/mt4setup.exe /auto    # /auto = silent install, no dialogs

# 4. Launch the app
cd "$WINEPREFIX/drive_c/Program Files (x86)/MetaTrader 4" && wine terminal.exe &

# 5. VNC server (daemonize with -bg)
x11vnc -display :99 -nopw -forever -shared -xkb -rfbport 5999 -bg -o /tmp/x11vnc.log

# 6. noVNC web frontend
websockify --web /usr/share/novnc 8080 localhost:5999 &

# 7. Public tunnel
/tmp/cloudflared tunnel --url http://localhost:8080 --no-autoupdate
```

URL printed by cloudflared: `https://<random>.trycloudflare.com/vnc.html`

## Production deploy (systemd-managed, survives reboot)

Write 8 service files (one per process layer). Each service is small and identical-pattern; see `templates/systemd-services.sh` for the full set. Pattern per service:

```ini
[Unit]
Description=MT4 wine terminal
After=xvfb-mt4.service
Requires=xvfb-mt4.service

[Service]
Type=simple
Environment=DISPLAY=:99
Environment=WINEPREFIX=/root/.wine-mt4
Environment=WINEARCH=win64
Environment=WINEDEBUG=-all
WorkingDirectory=/root/.wine-mt4/drive_c/Program Files (x86)/MetaTrader 4
ExecStart=/usr/bin/wine terminal.exe
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`Restart=always` + `RestartSec=5/10` makes each layer self-healing. If wine crashes, Xvfb dies, x11vnc dies, or the tunnel drops, the layer restarts automatically. The full deploy script (writes all 8 service files + nginx reverse proxy + anti-idle cron) is in `scripts/deploy_mt_stack.sh`.

## Resource use per instance

- RAM: ~300-400MB per running app (MT4/MT5 ~700MB combined)
- CPU: 5-10% idle, spikes on chart redraw
- Disk: 1-2GB per wine prefix after install

A 4GB VPS runs ~3-4 instances comfortably. A 15GB VPS runs 6-8. Each instance = one display + one wine prefix + one tunnel. They don't share state.

## Multiple instances on one VPS

Pattern: each app gets its own display number, wine prefix, VNC port, noVNC port, tunnel. The numbers just have to be unique per host.

| App | DISPLAY | WINEPREFIX | VNC port | noVNC port |
|-----|---------|------------|----------|------------|
| MT4 | :99 | /root/.wine-mt4 | 5999 | 8080 |
| MT5 | :98 | /root/.wine-mt5 | 5998 | 8081 |
| app3 | :97 | /root/.wine-app3 | 5997 | 8082 |

Each `Xvfb :N` and each `wine ...` is fully isolated. The two stack instances don't know each other exists.

## Re-running after a session/env reset

The wine prefixes and install state are NOT preserved across hard env resets (only the workdir is). After a reset, you must re-run steps 2-3 (init wine prefix + install app) per app. The systemd service file persists and the deploy script can be re-run end-to-end in ~5 min per app.

If the env reset only kills the display (not the prefix), just:
```bash
rm -f /tmp/.X99-lock /tmp/.X98-lock
Xvfb :99 -screen 0 1280x800x24 -ac &  # or start via systemd
Xvfb :98 -screen 0 1280x800x24 -ac &
x11vnc -display :99 -nopw -forever -shared -xkb -rfbport 5999 -bg
x11vnc -display :98 -nopw -forever -shared -xkb -rfbport 5998 -bg
websockify --web /usr/share/novnc 8080 localhost:5999 &
websockify --web /usr/share/novnc 8081 localhost:5998 &
wine <path to terminal.exe> &
/tmp/cloudflared tunnel --url http://localhost:8080 --no-autoupdate &
/tmp/cloudflared tunnel --url http://localhost:8081 --no-autoupdate &
```

## Pitfalls (learned the hard way)

- **`wine32 is missing` on first wine run.** Fix: `dpkg --add-architecture i386 && apt install wine32:i386`. Multiarch must be enabled BEFORE first `apt install wine64`.
- **`Bad EXE format` / `wine: could not load kernel32.dll, status c0000135`.** Root cause: wineprefix is 32-bit but the installer is 64-bit (PE32+). Fix: `rm -rf ~/.wine && export WINEARCH=win64 && wineboot --init`. Set `WINEARCH=win64` BEFORE the first `wineboot` — once a 32-bit prefix is created, `WINEARCH=win64` is ignored.
- **`Server is already active for display 99`.** Stale lock file from a crashed Xvfb. Fix: `rm -f /tmp/.X99-lock` then restart Xvfb.
- **x11vnc dies silently.** DISPLAY env not inherited properly when launched from a non-shell context. Fix: pass `DISPLAY=:99 x11vnc -display :99 ...` inline (NOT via export), AND use `-bg` flag to daemonize. Check `/tmp/x11vnc.log` for `The VNC desktop is:` line as proof it's listening.
- **ALSA errors in wine log.** "ALSA lib confmisc.c:767:(parse_card) cannot find card '0'" — harmless on a VPS with no sound card. Ignore.
- **cloudflared URL changes on every restart** (it's a quick tunnel). For a stable URL, register a named tunnel via `cloudflared tunnel login` + `cloudflared tunnel create <name>` + DNS record. For dev/testing, the random URL is fine.
- **The display is "active" only when something is on it.** A wine app that crashed leaves the display blank, but Xvfb itself stays up. Watch for "wine terminal.exe" / "wine terminal64.exe" in `ps aux` to confirm the app is actually running, not just Xvfb.
- **Wine ~700MB RAM per running instance.** Running 4-5 apps on a 4GB VPS causes heavy swap. Plan headroom.
- **noVNC needs `--web /usr/share/novnc`** on the websockify command, otherwise you get 404 on `/vnc.html`.

## When to use this vs alternatives

- **Use this when**: user wants a long-running Windows GUI app accessible from anywhere, no Windows machine, no RDP/teamviewer, no public IP needed.
- **Use X11RDP / xrdp instead if**: user has a public IP and wants true RDP (better mouse/keyboard latency, clipboard, file transfer). More setup, no NAT bypass.
- **Use VNC + SSH tunnel instead if**: VPS has SSH open and user is on a trusted network. Simpler than this stack.
- **Use Vagrant + VirtualBox instead if**: user wants to run actual Windows (not Wine). Heavier (needs Windows license, real disk, real CPU).
- **Use Kasm Workspaces / Apache Guacamole instead if**: user wants a multi-user brokered desktop gateway. Enterprise, not single-user.

## Deploying to a NEW VPS (the 3-step flow)

1. SSH into fresh Ubuntu VPS, run `bash deploy_mt_stack.sh` (see `scripts/`). ~5 min, no interaction.
2. Open the printed `trycloudflare.com` URL in a browser. noVNC loads.
3. Click "Connect" in the noVNC toolbar. The Windows app appears in the browser window with full mouse + keyboard.

For the user's case (Mohammad, 24/7 trading, free-tier VPS), the recommended free hosting:
- **Oracle Cloud Free Tier** — 1x ARM (4 OCPU + 24GB) free forever. Need CC for signup, instance can be reclaimed after 7 days idle (anti-idle script in deploy).
- **Hetzner Cloud** — €3.79/mo, CX22 (2 vCPU/4GB), reliable.
- **BuyVM** — $3.50/mo, 1GB, accepts crypto.

## Known-working apps via Wine on this stack

- ✅ MetaTrader 4 (terminal.exe) — tested 2026-09-04
- ✅ MetaTrader 5 (terminal64.exe) — tested 2026-09-04
- ⚠ TradingView desktop — works but heavy
- ⚠ Photoshop — slow but works for basic editing
- ❌ Most games — Vulkan/DirectX 12 not supported, no GPU

## Files in this skill

- `scripts/deploy_mt_stack.sh` — full Oracle Cloud / fresh Ubuntu deploy (8 systemd services + nginx + anti-idle)
- `templates/systemd-services.sh` — raw service file templates for any app
- `references/troubleshooting.md` — diagnostic recipes when a layer dies

## Verified working (2026-09-04)

- Server: Azure VPS, x86_64, AMD EPYC 7763, 15GB RAM, no GPU
- Both MT4 and MT5 ran simultaneously on display :99 and :98
- 20 background processes, ~700MB combined RAM
- Live URLs: https://succeed-biotechnology-andrew-deaf.trycloudflare.com/vnc.html (MT4), https://penny-eastern-venues-focusing.trycloudflare.com/vnc.html (MT5)
- User reaction: "This is actually crazy expalin how NOT how this works but the way you installed it"
