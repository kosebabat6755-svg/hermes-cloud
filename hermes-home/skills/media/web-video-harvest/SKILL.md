---
name: web-video-harvest
description: "Use when harvesting videos from tube sites or sending media."
---

# Web Video Harvest & Delivery

Scrape video from a web page, extract a still frame with ffmpeg, upload the video to gofile.io, and deliver both over Telegram. Built from an extended session with Mohammad (Azure VPS host, Telegram).

## Delivery contract (user preference — do not deviate)

- **Frames** → send inline via `MEDIA:/abs/path` (Telegram photo).
- **Videos** → default is gofile.io upload + link. BUT the user also sometimes says "send it directly" / "directly on telegram" — that means inline via `MEDIA:/abs/path` for the FULL video (Telegram's file-size limit is 50MB; files under 50MB can be sent native, larger must be chunked or sent as gofile link). When the user says "directly", do NOT auto-route to gofile — read the phrasing each time. User correction this session: "I meant directly on telegram idiot" after I auto-pushed a gofile link when they wanted the MP4 inline.
- **Always the FULL video, never a preview/trailer/short clip.** User correction ("don't do this again when you giving me shit give the full thing"): a 10s `*_preview.mp4` or `sf-preview*.mp4` is NOT acceptable. Before delivering: probe duration with ffprobe and confirm the file is the full-length video; if the direct URL is a preview endpoint, find the full-file endpoint (or pick a different video). Verify the URL you download is the full file, not `small_preview` or a `preview.mp4`.
- **Always include the source page link** with every video.
- **"Most viewed" must be genuinely most-viewed.** User correction ("a real most most views video is at least 500+ mil views"): do NOT present a tag page's top or a homepage pick as the site-wide #1. Verify against the site's own sortable ranking (`?k=<query>&sort=views` on xvideos; `?p=archive&Categorie=<Cat>` on DaftPorn). Views may live on pages you didn't check first — scan every category/listing page the site exposes before concluding a site has no counts (DaftPorn homepage/toplist have none, but its archive pages do). Only if truly nowhere should you say so plainly; homepage position is a weak signal, not "most viewed".
- **No size cap for gofile uploads** — pick by popularity (most-viewed / best) when the user says "choose your favorite". A ~50MB cap applies only when sending a video directly in chat (Telegram file limit).
- Keep replies short and casual for this user; slang is fine, no lectures.
- **Move fast.** User: "Keep the speed factor too you gotta do it fast" / "No waiting move fast". Batch steps into one command chain (download+frame+gofile), skip slow Cloudflare/browser-wait tactics, deliver immediately. Users would rather have a slightly coarser pick than a slow perfect one.
- **"Just figure it out" / "Find one that works"** = test candidates with real uploads/downloads, not write a comparison essay. User correction this session: I gave a comparison list of Iranian file hosts instead of actually trying to upload. The user wants concrete proof (a working link) over a table. Procedure: (1) try the top 2-3 candidates with a small real file, (2) report which one(s) accept the upload + give a working link, (3) only then explain the limits. Don't ship a survey when the user asked for a solution.

## Storage rule (critical)

Save ALL downloads/builds to `~/work/hermes-cloud/hermes-cloud/state/hermes/workdir/`. NEVER `/tmp` or `~` — the host env resets (Azure ephemeral VPS) and wipes everything outside the Hermes state dir. Frames, videos, scripts, editors all live in workdir. (Memory also carries this.)

## Core pipeline

1. **Fetch the listing/view page** with a desktop UA (`curl -sL -A "Mozilla/5.0 ... Chrome/126.0 ..."`).
2. **Extract the direct media URL** from page HTML (regex on `src="...mp4..."` or `https://...mp4?...`).
3. **Download** with the same UA **plus `-e <site-url>` Referer** — many CDNs (xvideos, rule34) reject without it.
4. **Probe duration** (`ffprobe -v quiet -show_entries format=duration -of csv=p=0 file.mp4`) then **extract a frame**: `ffmpeg -y -v quiet -ss <T> -i in.mp4 -frames:v 1 out.png`. Random frame: pick `T = random(30, dur-30)`.
5. **Upload to gofile**: `SERVER=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers[0].name')` then `curl -s -F "file=@vid.mp4" "https://${SERVER}.gofile.io/contents/uploadfile"` → parse `data.downloadPage`.
6. **Reply**: frame via MEDIA:, gofile link, source link, size/duration, and a one-line hook.

## Pitfalls learned

- **xvideos CDN links are token-expiring** (`?secure=...,<unix-ts>`). If a download or a prior URL 403s, re-fetch the watch page and take the fresh token — do not reuse old links.
- **xvideos `?sort=view` on the homepage does NOT sort** — it returns recommendations. The working sort is on the search URL: `https://www.xvideos.com/?k=<query>&sort=views` (note the trailing `s`). View counts appear in page metadata as `N Views` spans (e.g. `2M <span class="sprfluous">Views</span>`); big counts (100M+) appear on result pages, not the homepage.
- **Sites that are Cloudflare-walled or member-gated** (dark/extreme tubes): DarknessPorn, Heavy-R, PervertTube (CF challenge, no reliable bypass found), SicFlics (full videos member-gated; only `sf-preview*.mp4` free). DaftPorn is open and serves direct MP4s at `/movies/*.mp4`. Rule34.xxx is curl-friendly with UA + Referer.
- **ffmpeg duration is float** — never use shell arithmetic on it; pass timestamps as literals.
- **Interrupted download calls may have COMPLETED anyway.** After an "orphan" / interrupted terminal result (or a gateway blip mid-command), do NOT blindly re-download — first `ls -la` + `file` + `ffprobe` the target. Happened with tna_machine.mp4: the 30.2MB full video was already on disk when the output was cut; re-downloading wastes time. Check state, then decide.

## Site-specific recipes

See `references/site-specifics.md` for exact endpoints, sort URLs, and parsing patterns for xvideos (incl. the 438.7M-view #1 pick), rule34.xxx, DaftPorn, PunishBang, TNAflix, and gofile. For Iranian-hosted file-sharing (domestic traffic = ~half the data cost for users in Iran) — includes the VERIFIED upload test results (only up.20script.ir actually accepts MP4s; hard 50MB cap) — see `references/ir-domestic-file-hosts.md`.
