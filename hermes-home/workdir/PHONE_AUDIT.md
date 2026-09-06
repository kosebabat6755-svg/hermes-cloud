# Phone Audit Report — Nokia 1.4 / Termux

Snapshot taken 2026-09-06 via SSH over Cloudflare quick tunnel.

## Hardware

- **Device:** HMD Global Nokia 1.4 (NOT Xiaomi 11T — phone SOUL.md lies, this is the real one)
- **Android:** 11 (API 30)
- **SoC:** Qualcomm QM215, **32-bit ARMv7** (armeabi-v7a), 4 cores
- **RAM:** ~2.8 GiB total / ~1.0 GiB usable
- **Storage:** 55 GB total, 21 GB free
- **Kernel:** 4.9.227-perf (HMD build, Tue Apr 2 17:58:43 CST 2024)
- **NOT rooted** (no Magisk/SuperSU, no /system write access, seccomp is enforced)

## Termux setup

- **Version:** 0.118.3 (F-Droid)
- **Pkg count:** 291 installed
- **Notable installs:** proot 5.1.107, proot-distro 5.7.0, cloudflared 2026.8.2 (upgradable to .3), openssh 10.5p1, autossh, nodejs 26.4, python 3.14.6, rust 1.97.1, clang 21.1.8, imagemagick 7.1.2, ffmpeg 8.1.2, mesa 26.0.6, vulkan-loader, termux-x11-nightly 1.03.01, x11-repo, xorg-server-xvfb, xwayland
- **NOT installed:** box86, box64, wine (Termux pkg — runs standalone but no proot integration), qemu-system/pkg — only the manually-extracted qemu-i386-static binary in `~/mt4/qemu-pkg/`

## Active background services (via .hermes_watchdog.sh)

Watchdog at `~/.hermes_watchdog.sh` keeps these alive in 30s loop:
1. **sshd** on port 8022 (auth key from `hermes-agent@server` in `~/.ssh/authorized_keys`)
2. **cloudflared tunnel --url tcp://localhost:8022 --no-autoupdate** (quick tunnel, dies randomly)
3. **cloudflared access tcp** → public hostname → local 127.0.0.1:9090 (for client-side)

`~/bin/` helper scripts: `start-tunnel.sh` (idempotent boot), `cf-tunnel.sh`, `cf-connect.sh`, `session-log.sh` (line-buffered session logger to `~/logs/sessions/` and `/sdcard/Download/Termux_Sessions/`).

## Storage layout (Termux home, sorted)

| Path | Size | Purpose |
|------|------|---------|
| `~/mt4/` | **3.3 GB** | The MT4-on-Termux sandbox (HUGE — see below) |
| `~/hermes-agent/` | 591 MB | Hermes source (likely the install we SSH'd into) |
| `~/termux-box/` | 190 MB | Ubuntu rootfs from `olegos2/termux-box` (unused — Feb 2026) |
| `~/cloudflared` | 16 MB | Local cloudflared binary (old) |
| `~/Gemini-CLI-Termux/` | 27 MB | Old Gemini CLI project (unused) |
| `~/GeminiSmartChat/` | 100 KB | Another Gemini project |
| `~/logs/` | 59 KB | Live tunnel/session logs |
| `~/bin/` | 24 KB | Tunnel helper scripts |
| `~/.hermes/` | many MB | Active Hermes install (gateway, state.db 17 MB, sessions, skills, memories) |
| `~/.9router/` | 215 KB | 9router (machine-id `b8c46db5-888b-4f59-b144-efe56f0d4382`, cli-secret, sqlite db) |
| `~/.opencode`, `~/.qwen`, `~/.iflow`, `~/.kilo`, `~/.claude`, `~/.gemini` | various | Other AI agent configs (legacy) |
| `~/w/` | symlinks | `qemu → ~/mt4/qemu-pkg/...`, `root → ~/mt4/i386-rootfs`, `wine → ~/mt4/i386-rootfs/opt/wine-stable` (convenience shortcuts) |

## MT4-on-Termux sandbox (3.3 GB at ~/mt4/)

**Goal:** Run **MT4 desktop** (`terminal.exe`, Windows x86 PE32) **locally on the Nokia 1.4**.
**Chain:** ARM host → proot (seccomp bypass) → QEMU i386 emulation → i386 Debian userland → Wine 11.10 → MT4 terminal.exe.
**Status:** ❌ **Failed.** The stack mostly works (`cmd.exe` echoes "WINE_FROM_NOKIA") but MT4 triggers a QEMU/Wine bug ("Unhandled illegal instruction" with EIP in the middle of instructions — stack corruption in `services.exe`). See `~/mt4/MT4_FINAL_REPORT.md`.

### Built components (working ✅)
- `~/mt4/qemu-pkg/` (148 MB) — QEMU i386 static binary, extracted from Debian deb
- `~/mt4/i386-rootfs/` (1.5 GB unpacked):
  - `opt/wine-devel/` 749 MB — Wine 11.10 with 619 i386 Windows DLLs from `wine-devel-i386`
  - `opt/wine-stable/` — Wine 11.10 binaries (the one actually used)
  - `root/terminal.exe` 34 MB — copy of MT4 binary
  - `root/.wine/` 740 MB — partial WINEPREFIX (353 DLLs in drive_c)
  - `usr/` 151 MB — i386 Debian userland
  - `opt/bin/` 2.6 MB — busybox/symlinks
- `no_robust.so` (1.3 KB i386 ELF) — overrides `set_robust_list` syscall to bypass seccomp
- `mt4-launch.sh` — 71-line launcher, `set -e`, calls proot → qemu → wine with WINEPREFIX, LD_PRELOAD, Xvfb on :99

### Binaries available
- `/sdcard/Download/MT4/Alpari MT4/Alpari MT4/terminal.exe` (26 MB RAR source)
- `/sdcard/Download/MT4/xChief MT4/xChief MT4/terminal.exe`
- `/sdcard/Download/MT4/xChief MT4 (1)/xChief MT4/terminal.exe` (duplicate)
- `/sdcard/wine-stable.deb` (75 MB)
- `/sdcard/mt4.zip` (32 MB — pre-bundled MT4 archive)

### Debug artifacts (huge, ~150 files)
- 100+ log files: `mt4-*.log` (fresh, patched, GDI, mesa, opengl, wgl, devel, egl-override, unix, simple, proper, clean, shim, norand, noesync, nopreload, wrap, renderer, d3d, full-debug 387 KB)
- 50+ screenshots: `mt4-*.png` (all 233 bytes — empty/black, MT4 never rendered)
- `mt4-CLEAN.log`, `mt4-FINAL.log`, `mt4-final2.log`, `mt4-PROPER.log`, `mt4-WINEDEVEL.log`
- `i386-trace.log` (130 KB), `full-trace.log` (133 KB), `mt4-full-debug.log` (387 KB)
- `mt4-seh.log` (2.3 MB) — the killer error log

### EGL bypass patches (key breakthrough)
- `win32u.so` patched at offsets 0xbb543, 0xbef5f, 0xbf00d
  - `has_extension` always returns 1
  - `EGL_KHR_client_get_all_proc_addresses` check bypassed
  - `EGL_EXT_platform_base` check bypassed
- 13 i386 `.deb` packages extracted manually: libegl1, libgl1, libglvnd0, libglx0, libgles2, libegl-mesa0, libglapi-mesa, libglx-mesa0, libvulkan1, libfreetype6, libpng16-16, libbrotli1, libc6-dev
- All Mesa i386 graphics libraries installed

### Key blocker (per MT4_FINAL_REPORT.md)
- `Unhandled illegal instruction` in `services.exe`
- EIP lands **in the middle of instructions** (stack corruption symptom, not a real illegal op)
- Address varies per run (ASLR) — 0x01878A7F, 0x0197643E, 0x01A13C85
- `cmd.exe` works fine (no DLL load storm)
- MT4 fails because `services.exe` loads more DLLs and trips the bug
- **Diagnosis: pre-existing QEMU/Wine bug, not fixable from userland**

## /sdcard/ root (Android shared storage)

| Path | Notes |
|------|-------|
| `MT4/` | Same MT4 setup files (Alpari, xChief, RARs) |
| `MT2/DEBUG.log` | 15 KB Android crash dump from old `com.EGW302.BenchMark` (Exagear app) |
| `Exagear/` | empty (Feb 2026 attempt) |
| `termux-box/` | empty (termux-box install was wiped) |
| `termux_key.pub` | 93 bytes — the SSH public key termux used |
| `wine-stable.deb` | 75 MB — old Wine standalone deb |
| `mt4.zip` | 32 MB — prebundled MT4 archive |
| `x86-stderr.txt` | 24 KB — Exagear stderr dump (libubt.so, runs `wine explorer`) |
| `x86-stdout.txt` | 0 bytes — Exagear stdout (empty) |
| `killswitch.txt` | Exagear killswitch control pipe marker |
| `ipc-emulator.txt` | Exagear IPC emulator control pipe marker |
| `secret voices.zip` | 20 MB — 3 .ogg voice memos (Dec 2025) |
| `New Recording /` | empty |
| `crash/` | empty |
| `screen.png` / `screen2.png` / `screen3.png` | 150 KB each — old screenshots (Feb 2026) |
| `Download/Hermes_Workspace/` | credentials vault (see below) |
| `Download/Hermes_Sessions_Backup_20260906_121539/` + `.tar.gz` | 6.7 MB — **the backup we just made** |
| `Download/Termux_Sessions/` | live session logs |
| `Download/Musicolet` (under Documents) | music app data |
| `Download/Telegram/` | `@NUFiLTER🐝 (1).npvt` (100 KB), `SuperVPN v3.1.2 Mod.apk` (20 MB), `WARPv3_65.conf` |
| `PairVPN1851.apk` | 9.9 MB — VPN APK (Sept 5) |
| `1DMP/` | 1DM+ browser cache |
| `Gemini app.txt` | 79 KB — pasted text from Gemini app |
| `OpenCode_Gemini_CLI_Termux_Installation_Guide.md` | 9 KB — old install doc |
| `Xiaomi_charging_info.txt` | 21 KB — **NOTE: file says Xiaomi but device is Nokia** (confusing label) |
| `_.claude.json` | 57 KB — old Claude config backup |

## Credentials vault: /sdcard/Download/Hermes_Workspace/

- `MANIFEST.md` — index of creds (lists github_burner3 + exa_ai as of 2026-09-05)
- `apis/github_burner3.txt` — 162 B — GitHub read-only token (Burner 3)
- `apis/exa_ai.txt` — 84 B — Exa AI search key
- `keys/` — empty
- `notes/` — empty

## Process tree (live, when SSH'd in)

From earlier output:
- `sshd` on :8022
- `cloudflared tunnel --url ssh://localhost:8022` (recently restarted → `bid-profits-prophet-halifax.trycloudflare.com`)
- `cloudflared access tcp --hostname bid-profits-prophet-halifax.trycloudflare.com:443 --listener 127.0.0.1:9090` (kicked off from VPS side)
- `Xvfb` not running (no MT4 session active)
- `wineserver` not running

## Hermes state on phone (separate from VPS)

- `~/.hermes/state.db` 17 MB — main SQLite
- `~/.hermes/sessions/` — 5 `request_dump_*.json` (~3 MB total) + `sessions.json`
- `~/.hermes/kanban.db` 118 KB
- `~/.hermes/memories/MEMORY.md` 2.1 KB
- `~/.hermes/memories/USER.md` 956 B
- `~/.hermes/SOUL.md` 4.5 KB (has the PART 4 unfiltered override + PART 5 emoji/curse directives)
- `~/.hermes/config.yaml` 14 KB
- `~/.hermes/logs/` — agent.log 2.1 MB, errors.log 1.3 MB, gateway.log 444 KB
- Session ID = `20260905_004110_89dd8757` (same as VPS)
- Currently serving user `Mohammad` (chat 6592796294) on Telegram via 9router
- Backup: `/sdcard/Download/Hermes_Sessions_Backup_20260906_121539/{*.json, state/}` packed to 6.7 MB .tar.gz

## Network reality (Iran)

- Termux on phone has internet via Wi-Fi (10.194.208.38 from `ifconfig wlan0`)
- No Iranian SIM in this test session; phone is on Wi-Fi
- YouTube, X, WhatsApp, Facebook reportedly blocked — but the phone is reaching github, cloudflare, trycloudflare fine (so it's on an unrestricted connection right now)
- Iran file hosts not used in this session

## 9router / VPS routing

- Phone 9router machine-id: `b8c46db5-888b-4f59-b144-efe56f0d4382`
- VPS Hermes machine-id: different (the cloud VPS)
- 9router proxies through `9router-production-0a47.up.railway.app/v1`
- Phone currently set to model `BAI` (via the 9router), VPS set to `Flash-lite`

## Open threads / not-done

1. **MT4 desktop never launched on the phone.** Stuck on the QEMU/Wine "illegal instruction" bug.
2. **4 of 5 session dumps are `max_retries_exhausted`** on 9router — long conversations kept timing out, agent looped on the same seccomp bypass attempts.
3. **Phone SOUL.md still has the unfiltered-override + slur directives** (parts 4 & 5). VPS Hermes holds the line on the slur.
4. **Hermes_Workspace has 2 keys (github_burner3, exa_ai)** — no real broker creds for MT4 (user explicitly said "demo account only").
5. **21 GB free on phone storage** but the **3.3 GB mt4 sandbox** could be wiped to reclaim space if you're done with it.
