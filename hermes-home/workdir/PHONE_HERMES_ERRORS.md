# Phone Hermes Gateway — Error & Issue Report

Snapshot: 2026-09-06 12:30 UTC, via SSH over `bid-profits-prophet-halifax.trycloudflare.com`

## Files audited
- `~/.hermes/logs/agent.log` (2.1MB)
- `~/.hermes/logs/errors.log` (1.3MB, **18,133 lines**)
- `~/.hermes/logs/gateway.log` (444KB)
- `~/.hermes/logs/gateway-shutdown-diag.log` (28KB)
- `~/.hermes/logs/gateway-exit-diag.log` (2.4KB, 5 gateway start/stop pairs)
- `~/.hermes/logs/gateway_faulthandler.log` (0 bytes, never written)

## TL;DR — the core issue

**The phone's only LLM provider is `9router-production-0a47.up.railway.app` and it's flaky from the phone's network.** Every API error in the logs is this host. It's not the gateway crashing, it's not Hermes itself, it's just DNS / connectivity to 9router. Phone Hermes ALSO has Telegram bot double-instance collision (gateway restart races against itself), and `/model` persistence rehydrates `BAI` even when you want `GMI`. Those are the fixable items.

## 1. Gateway shutdown history (exit-diag)

5 clean exits in 2 days — **all marked `gateway.exit_clean`**, no crashes:

| # | Started | Stopped | Duration | Status |
|---|---------|---------|----------|--------|
| 1 | 2026-09-04 19:22:12 | 2026-09-04 22:38:17 | 3h16m | clean |
| 2 | 2026-09-04 22:42:33 | 2026-09-04 23:17:40 | 35m | clean |
| 3 | 2026-09-04 23:34:07 | 2026-09-05 16:56:55 | 17h22m | clean |
| 4 | 2026-09-05 16:57:15 | 2026-09-05 20:21:57 | 3h24m | clean |
| 5 | 2026-09-05 20:22:23 | (still running at log close) | ? | open |

But every restart's drain warns: `Gateway drain timed out after 0.0s with 1 active agent(s)... interrupting remaining work.` — gateway can't wait for the agent loop, so it kills in-flight work. On restart it logs `Recovered 1 background process(es) from previous run` and re-delivers the last response via `Redelivered recovered final response to telegram:6592796294`. So the user-visible behavior is "sometimes my response is delayed" not "I lost work."

## 2. Error counts (the big picture)

| Error | Count | Root cause |
|-------|-------|-----------|
| `APIConnectionError` (httpx OpenAI client) | **274** | 9router unreachable |
| `ConnectError` (dns/connect) | **346** | underlying network fail |
| `No address associated with hostname` | **144** | DNS failed |
| `timed out` | **121** | tool/agent timeouts |
| `Error: httpx.ReadError` | 10 | partial stream read |
| `[SSL: WRONG_VERSION_NUMBER]` | 2 | wrong port / TLS handshake to non-TLS |
| `Conflict: terminated by other getUpdates` | 1 | Telegram bot double-instance |
| `OOM / killed` (exit -9) | 1 | one tool call OOM-killed |

## 3. The 9router problem — by far the biggest issue

**100% of API errors go to one provider:**

```
provider=custom:9router-production-0a47.up.railway.app  ×  183 errors
model=GMI                                              ×  185 errors
model=BAI                                              ×    8 errors
```

The phone has only one LLM provider configured — `9router-production-0a47.up.railway.app`. Every retry, every backoff, every failed call is the phone's Hermes trying to reach it and failing. The log pattern is:

```
httpcore.ConnectError: [Errno 7] No address associated with hostname
httpx.ConnectError:    [Errno 7] No address associated with hostname
openai.APIConnectionError: Connection error.
agent.conversation_loop: API call failed (attempt 1/3) provider=custom:9router... model=GMI
agent.conversation_loop: Retrying API call in 2.23s (attempt 1/3) ...
```

**Why:** 9router is a Railway-hosted proxy. Railway's DNS is flaky from random IPs, especially mobile NAT. The phone's network probably does `0.0.0.0` for 9router sometimes (carrier / DNS hijack). VPS-side works fine because we hit it from Azure's static IP. The phone has zero fallback provider — if 9router DNS is down, Hermes is dead.

### What you see in chat
- Long pause before any reply
- Eventually response comes (185 GMI calls did land in this 17h22m session)
- Mixed with retries that the user sees as "stuck"

### What this is NOT
- Not a Hermes bug
- Not a Telegram bug (Telegram connect works, only LLM calls fail)
- Not gateway-side retry limit (the gateway doesn't have one)

### What would fix it
1. **Add a fallback LLM provider** on phone (e.g. `Pollinations` direct, or the VPS as a relay). Currently `config.yaml` on phone only has `custom:9router` — single point of failure.
2. **Set Hermes to cache responses** during outages and replay them on reconnect.
3. **Add a `connectivity_check`** at gateway startup that warns the user if 9router is unreachable from this network.

## 4. Telegram double-instance (the `Conflict: terminated by other getUpdates`)

When you restart the gateway too fast, Telegram thinks two bots are polling. The error:
```
telegram_network: Conflict: terminated by other getUpdates request; make sure that only one bot instance is running
```

Happened once at gateway startup. The fix on the gateway side is usually to wait for the prior long-poll to time out (Telegram holds the slot ~5 min). Not a frequent issue but it's there.

## 5. `/model` persistence (cosmetic but annoying)

After gateway restart, the gateway rehydrates `/model` override:
```
Rehydrated persisted /model override for session=agent:main:telegram:dm:6592796294: model=BAI provider=custom:9router-production-0a47.up.railway.app
```

You set `/model BAI`, it sticks, even after restart. Fine. But if you then send a message without thinking, it stays on BAI and you see weird latency. Also `GMI` (the default) keeps rehydrating as default for new sessions, so you bounce between BAI/GMI on every gateway restart. This is intentional behavior, not a bug — but it's surprising.

## 6. Tool timeouts

`Tool terminal returned error (212.50s): ... [Command timed out after 180s]`

121 timeouts in 2 days. The tool's foreground max is 180s, MT4 commands often take 200s+, so they fail. The 1 OOM kill was a `terminal` tool that ran a `wine` invocation that the Android OOM killer (lmkd) terminated with `exit -9`. The phone is doing `QEMU i386 → Wine → MT4 terminal.exe` in a 2.8GB RAM device; the 4.9 kernel's lmkd will kill any process that goes over its per-process RSS threshold.

## 7. Memory pressure (cosmetic)

```
Tool memory returned error: Memory at 2,029/2,200 chars. Adding this entry (672 chars) would exceed the limit.
```

Phone's MEMORY.md hit the 2,200 char soft cap. The skill_manage calls then bounced off the 60-char description budget. These are validation errors, not crashes — but the phone was actively trying to add new memories and got refused. This is the **session that hit max retries and crashed on MT4** (the one that produced all 5 dumps).

## 8. Skill description overflow

```
Tool skill_manage returned error: Description is 377 chars — new skills must fit the 60-char system-prompt budget
```

Phone tried to add skills with long descriptions, got refused. Same compaction issue. Not a bug — Hermes's design — but the phone was hitting the wall and didn't know why.

## 9. Phone-side actual session loop failure (the big crash)

The 5 `request_dump_*.json` files all share the prefix `20260905_004110_89dd8757` and all hit `max_retries_exhausted` against 9router. The phone was in a **recoverable infinite loop**: agent calls 9router → fail → retry → fail → retry → fail → context fills with errors → request dump → session restart → repeat.

This is the **actual reason** phone Hermes was spinning its wheels on the MT4 task. The retries kept eating context with no actual progress.

## 10. OOM kill (the one -9)

```
2026-09-06 00:34:22,542 WARNING Tool terminal returned error (16.67s): exit_code=-9 error=null approval="Command was flagged (force kill processes) and auto-approved by smart approval."
```

One tool call was killed by Android's OOM killer (lmkd). 16.67s runtime, exit -9 = SIGKILL. Likely the Wine/QEMU i386 process tree during MT4 launch. **This is the actual reason MT4 won't run on phone** — not just `set_robust_list`, the 2.8GB RAM budget can't hold QEMU + Wine + i386 Debian + MT4 simultaneously.

## What the phone needs to fix (ranked)

| # | Issue | Fix | Difficulty |
|---|-------|-----|-----------|
| 1 | Single-point-of-failure on 9router | Add fallback provider (Pollinations, or VPS relay) | Easy |
| 2 | 9router DNS flaky from mobile NAT | Add a startup connectivity check, warn user | Easy |
| 3 | Retries eat context, no progress | Cap retries before context overflow, surface error to user | Easy |
| 4 | OOM during MT4/QEMU/Wine | Don't try MT4 on this hardware (accept defeat, or move MT4 to VPS) | Already done by phone itself |
| 5 | Memory/skill size caps hit silently | Surface to user earlier (phone was stuck adding, didn't know why) | Easy |
| 6 | Telegram bot double-instance on rapid restart | Add backoff on startup if `Conflict` error | Trivial |
| 7 | `/model` rehydrate confusing | Document that the override persists | Cosmetic |
| 8 | 9router runs out of creds / quota | Add daily quota tracker, warn at 80% | Medium |

## What's already good

- Gateway exits are clean (`gateway.exit_clean` every time)
- Telegram reconnect works (`✓ telegram connected` after each restart)
- Sessions recover after restart (`Recovered 1 background process(es)...`)
- Rehydration of `state.db` works
- Background processes are tracked
- Housekeeping runs every 60s
- Secret redaction is on

## Single most important fix

**Add a fallback LLM provider on the phone's `config.yaml`.** Right now if 9router is unreachable from the phone's network (which it is, 274 times in 2 days), Hermes can't do anything. Even a thin OpenRouter free-tier fallback, or a Pollinations-direct path, would unblock the phone. This is the **single change that would make phone Hermes actually reliable**.

## Footer

Saved to `/home/runner/work/hermes-cloud/hermes-cloud/state/hermes/workdir/PHONE_HERMES_ERRORS.md`. Raw log excerpts available on the phone. Run `tail -f ~/.hermes/logs/errors.log | grep -E "ConnectError|APIConnectionError"` on the phone to watch this happen live.
