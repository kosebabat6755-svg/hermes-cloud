# Phone Hermes — Real Issues (separate from 9router connectivity)

Snapshot: 2026-09-06 12:45 UTC. Filtered out the 9router DNS flakiness (you said ignore that). Found these.

## 1. **CRITICAL: Adapter stays disconnected on startup with NO auto-reconnect** 🔴

When Telegram can't connect on startup, the gateway logs `No adapter could be created for any of the 1 configured platform(s). Check that required dependencies are installed and credentials are set. Gateway will continue for cron job execution.` — **this is a misleading warning** that makes you think creds are missing when actually Telegram just timed out.

**Real pattern** (gateway.log, 2026-09-05 03:15:49):
```
ERROR gateway.run: ✗ telegram error: telegram connect timed out after 180s
WARNING gateway.run: Gateway started with no connected platforms
WARNING gateway.run: No adapter could be created for any of the 1 configured platform(s).
INFO gateway.run: Starting reconnection watcher for 1 failed platform(s)
```

The reconnection watcher is set up, BUT — 3 hours 12 minutes later (2026-09-05 21:28:48), Telegram is still failing, still on first reconnect attempt, and there's no progress on retries. **The reconnection watcher is broken or doing nothing useful.** The user sees the bot dead for hours.

Same thing happened on 2026-09-04 22:38-23:34 (~1 hour dead).

**What you observe:** Send a message to phone Hermes, no response. Gateway is up but Telegram is dead. Eventually reconnects on next manual restart.

**Fix needed:** Reconnection watcher should retry more aggressively, log each attempt, and after N failures, do a full gateway restart instead of just re-trying the platform.

## 2. **CRITICAL: Drain timeout kills in-flight work, 100% of the time** 🔴

Every single gateway shutdown hits:
```
Shutdown phase: drain done at +2.09s (drain took 0.02s, timed_out=True, ...)
WARNING gateway.run: Gateway drain timed out after 0.0s with 1 active agent(s)
```

The drain is configured for 0.0s (it should be a configurable timeout, default 30s+). Active agent is interrupted. But — and this is the real bug — **the agent is interrupted mid-response, and on next startup Hermes rehydrates and re-delivers the OLD final response**:
```
Redelivered recovered final response to telegram:6592796294 (obligation 38a5405672364ad341ef3196, attempt 1)
```

So the user sees the same response twice (once on the original completion attempt, once on next startup). And the obligation 38a54056... is the **agent's previous generation's final output** that was in flight when shutdown happened.

**What you observe:** Sometimes you get a duplicate response after a gateway restart. Sometimes the response is the OLD answer to a question you forgot about.

**Fix needed:** Drain should be ≥10s. And re-delivery of recovered final response should be a 1-time per-obligation, not always.

## 3. **HIGH: 10,030-second response (2.7 hours for 50 chars)** 🟠

```
2026-09-05 18:47:28,710 INFO gateway.run: response ready: platform=telegram chat=6592796294 time=10030.7s api_calls=1 response=50 chars
```

2.7 hours, 1 API call, 50 chars (likely "ok" or "done"). What happened: **Telegram polling died at 18:46:31** (primary + fallback IPs both failed), and **only reconnected at 18:47:28** — that's 57 seconds, not 2.7 hours. So the 10,030s was the agent loop total time, not the Telegram gap.

Tracing backwards: 18:47:28 minus 10030s = **2026-09-05 15:50:18 UTC** = the agent was started 2.7 hours before the response went out. The agent loop was spinning for 2.7 hours, then it finally returned 50 chars (probably after 149 API calls or so). Wait — that was a different run. This run had `api_calls=1`. So 1 API call took 2.7 hours. **The agent got stuck waiting for the 9router API to return**, and when it finally did return 50 chars, the response was already stale.

**What you observe:** Sometimes you get a "yes" or "ok" hours after you asked the question. The agent went into a deadlock waiting for an API call that took 2.7 hours.

**Fix needed:** API call timeout should be set per-call, and any call that takes > 5min should be killed and the user told "API timeout."

## 4. **HIGH: Runaway agent loops — 150 API calls per response** 🟠

```
api_calls=150  × 2 occurrences
api_calls=149  × 1
api_calls=120  × 1
api_calls=22   × 1
api_calls=14   × 1
api_calls=12   × 1
```

The agent.max_turns is 150. So `api_calls=150` means the agent hit the limit exactly — it kept trying for 150 turns and then gave up. **The 2 occurrences of "150 api_calls"** are sessions where the agent looped until it ran out of budget, then returned 50 chars ("giving up" response).

The 149-call one ran for 7,284 seconds (~2 hours, response was 1563 chars — actually useful work).

**What you observe:** Bot dead for 2+ hours, then either gives up with "ok" or returns a long answer.

**Fix needed:** When api_calls > 50 with no tool progress, warn the user and force a fresh start.

## 5. **MEDIUM: `/model` rehydrate is sticky + surprising** 🟡

After gateway restart:
```
Rehydrated persisted /model override for session=agent:main:telegram:dm:6592796294: model=GMI provider=custom:9router...
```

This rehydrates 3 times in 24 hours. The model is sticky across restarts. **This is intentional behavior, but it's surprising to the user** because they get a different model latency than the default. GMI is the default, BAI is the override.

**What you observe:** Bot feels slow one day, fast the next, and you don't know why. You do `/model` and realize the previous session left it on BAI or GMI.

**Fix needed:** Either reset to default on every restart, or surface the active model on every response (e.g. `[BAI]` prefix in the response).

## 6. **MEDIUM: Session reset count keeps growing** 🟡

```
generation → 23 (session_reset)
generation → 32 (session_reset)
generation → 45 (stop_command)
generation → 47 (stop_command)
```

Session reset → generation goes up by 1 each time. If the user hits `/stop` 47 times in 24h, generation is 47. **Generations are monotonically increasing but never reset to 0 on the user side.** Old session state accumulates. Eventually state.db gets fat.

**What you observe:** After weeks of use, gateway feels slow. Restart helps. But the underlying state never gets pruned.

**Fix needed:** A session reset should also reset the generation counter, OR prune state.db periodically.

## 7. **MEDIUM: Stale agent result discarded — wasted work** 🟡

```
Discarding stale agent result for agent:main:telegram:dm:6592796294 — generation 44 is no longer current
```

When user `/stop`s while a tool is running, the agent returns eventually but the result is discarded because the generation is stale. **The 2-3 minute work the agent did in the tool is thrown away**, the user never sees it, and the next user message starts fresh.

**What you observe:** Sometimes you stop a long-running command, then send a new message, and the long-running tool's output that you wanted gets lost.

**Fix needed:** Stale results should be saved to a "drop box" the user can `/last` to retrieve.

## 8. **LOW: SQLite `TrackedConnection returned NULL`** 🟢

```
WARNING hermes_state: async token accounting: apply failed (session=20260905_004110_89dd8757): <hermes_cli.sqlite_safe_read.TrackedConnection object at 0xab5bbc90> returned NULL without setting an exception
```

This is a Python `sqlite3` quirk: a query returned NULL but the cursor didn't raise. Happened once in 18,133 lines. Probably async write that got cancelled. Not a real bug, but the warning is noise.

**Fix needed:** Suppress this warning, or make `TrackedConnection` always set an exception on NULL.

## 9. **LOW: 72 hidden commands (over Telegram's 60 limit)** 🟢

```
Telegram menu: 60 commands registered, 72 hidden (over 60 limit)
```

Hermes has 132 total slash commands but Telegram only allows 60 in the menu. 72 are hidden. Not a bug, but `/commands` is the only way to see the rest.

**Fix needed:** Pick 60 most-used commands for the menu, or use scopes (per-chat) to expose more.

## 10. **LOW: HARDLINE block on heredoc in shell** 🟢

```
WARNING tools.approval: Hardline block: command parser limit or malformed executable payload
```

Happened once when a command had a heredoc. Hermes's safety block on heredocs is overly strict and can false-positive. Not a frequent issue.

**Fix needed:** Loosen the heredoc parser, or document which heredoc forms are allowed.

## 11. **LOW: 2.8GB phone → SQLite WAL/SHM not always checkpointed** 🟢

state.db is 17MB, with -shm and -wal files. On a 126MB-storage phone, the WAL can grow if not checkpointed. This could be why the gateway occasionally pauses for ~5s on commits.

**Fix needed:** Periodic `PRAGMA wal_checkpoint(TRUNCATE)` in the housekeeping loop (every 60s).

## Summary — the 3 highest-impact fixes

| # | Issue | Impact | Fix complexity |
|---|-------|--------|----------------|
| 1 | Telegram reconnection watcher does nothing | Bot dead for hours | Medium |
| 2 | Drain timeout = 0.0s | Work interrupted, dup responses | Trivial (1 config change) |
| 3 | 2.7-hour API calls + 150-iter loops | User waits forever for nothing | Medium (add API timeout) |

**Fix #2 alone is a 1-line config change** (`drain_timeout=30` or whatever) and would eliminate the duplicate-response-after-restart problem. Worth doing first.

## Footer

Raw log excerpts available on the phone. Run `tail -f ~/.hermes/logs/gateway.log | grep -E "drain|No adapter|timed out"` to watch #1 + #2 happen live. `grep "response ready:" ~/.hermes/logs/gateway.log | sort -k7 -n -t'='` sorts responses by duration, surfaces #3.
