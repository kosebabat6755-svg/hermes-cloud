---
name: termux-session-logger
description: Use when the user wants every Termux shell session auto-logged to disk + sdcard. Bash script + bashrc hook that tee-logs interactive shells to ~/logs/sessions/ and mirrors to /sdcard/Download/Termux_Sessions/.
---

# Termux Session Logger (auto-every-shell)

Mamad's setup. Captures every interactive Termux shell session to a dated log file, mirrors to sdcard so it's visible in the Android Files app. Logs survive phone reboots because they live on the sdcard side.

## What it does

Every new interactive bash shell:
1. Creates a fresh log file named `YYYYMMDD_HHMMSS_<label>_<pts>.log`
2. `tee -a`'s all stdout+stderr into the local copy at `~/logs/sessions/`
3. Background `setsid bash -c "tail -f | while read line..."` mirrors new lines to `/sdcard/Download/Termux_Sessions/`
4. Prints a banner: `SESSION LOGGING ACTIVE / pts: pts_1_ / started: ... / local: ... / sdcard: ... / disable: close this session`
5. Exposes env vars: `SESSION_LOG_FILE`, `SESSION_LOG_MIRROR`, `SESSION_LOG_PID=$$`, `SESSION_MIRROR_PID=$MIRROR_PID`

## Files

| File | Purpose |
|------|---------|
| `~/bin/session-log.sh` | The wrapper script (~4.4KB) |
| `~/.bashrc` | Auto-sources the script in interactive shells |
| `~/logs/sessions/` | Local log directory (per-session file) |
| `/sdcard/Download/Termux_Sessions/` | Sdcard mirror (Android Files app) |
| `/sdcard/Download/session-log-system.tar.gz` | Full backup of the system (on phone, 19KB) |

## Install on a fresh Termux

```bash
# 1. Create dirs
mkdir -p ~/bin ~/logs/sessions
mkdir -p /sdcard/Download/Termux_Sessions

# 2. Drop the script at ~/bin/session-log.sh
#    (Copy from session-log-system.tar.gz → bin/session-log.sh)
chmod +x ~/bin/session-log.sh

# 3. Add the bashrc hook (see below)
#    ~/.bashrc must contain:
#       case "$-" in *i*) ;; *) return 0 ;; esac
#       if [ -z "$SESSION_LOG_FILE" ] && [ -f "$HOME/bin/session-log.sh" ]; then
#         SESSION_LABEL="${TERMUX_SESSION_LABEL:-auto}"
#         source "$HOME/bin/session-log.sh" "$SESSION_LABEL"
#       fi

# 4. Open a new Termux shell — banner should print
```

## Customize label

Set `TERMUX_SESSION_LABEL=mywork` in env before opening a shell, or pass as arg: `source ~/bin/session-log.sh mylabel`. Default is `auto`.

## Disable

- Per-session: open a shell with `TERMUX_SESSION_LABEL=""` env unset, or `unset SESSION_LOG_FILE` before sourcing.
- Permanently: comment out the bashrc hook.
- The script's `--off` flag is a no-op (the wrapper docstring admits this — "cannot disable an already-running logger from here. Close this session and reopen").

## Key design choices baked into the script (do not regress)

1. **`pts/2` → `pts2` sanitization** — `ps -o tty= -p $$` returns `pts/2` which contains a slash that breaks any path it's spliced into. Sanitize via `tr -c 'A-Za-z0-9' '_'`.
2. **Pre-touch log files** — `tee` and the background `tail` race against the first stderr write if files don't exist yet. Pre-`: > "$LOG"` before the `exec >` redirect.
3. **Single-writer pattern** — `tee` writes to ONE file at a time (local), then a separate background `tail -f` mirrors to sdcard. Don't `tee` to two files simultaneously — the timestamp formatter races and drops interleaved bytes.
4. **Line-buffered tee** — `stdbuf -oL -eL tee` so `tail -f` shows output as it's written, not on block flush.
5. **setsid for the mirror** — `setsid bash -c "..."` so the mirror survives parent shell exit and doesn't keep the parent alive when sourced. `disown` for good measure.
6. **Sdcard failure → fall back to local** — `: > "$SD_LOG" 2>/dev/null || SD_LOG="$LOCAL_LOG"` — if sdcard is not mounted (rare but possible in some Termux configs), logging still works locally.
7. **Idempotent re-source guard** — `if [ -n "$SESSION_LOG_FILE" ] && [ -f "$SESSION_LOG_FILE" ]; then return 0` prevents the bashrc from double-wrapping if the script is sourced twice.

## Backup (so we never lose it)

Tarball the whole system to a known place:
```bash
cd ~
tar -czf /sdcard/Download/session-log-system.tar.gz \
  bin/session-log.sh .bashrc logs/sessions/
```
Pull back via `scp -P 9090` over the cloudflared tunnel to VPS workdir. The full system is ~19KB.

## Restore from backup

```bash
# On the new phone, after `scp`ing the tarball:
mkdir -p ~/bin ~/logs/sessions
tar -xzf session-log-system.tar.gz -C ~/
# shell/login/logout and the hook auto-fires
```

## History

Built by Mamad on 2026-09-04. Originally to debug MT4/QEMU work on Nokia 1.4 — session logs captured every command + output across many days. Survived the MT4 build attempts and got captured in the system tarball on 2026-09-06.

## Source backup location

- **On the phone:** `/sdcard/Download/session-log-system.tar.gz` (19KB, MD5 726edb93d64a914eac8e3f908818fc94)
- **On the VPS:** `/home/runner/work/hermes-cloud/hermes-cloud/state/hermes/workdir/session-log-system.tar.gz` (same MD5)
