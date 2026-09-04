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

**Env-reset recovery (verify on every fresh session / after interruption):** The workdir path itself can be deleted on a hard reset, AND helper binaries (ffmpeg, ffprobe, ffmpeg-related Python tools) get blown away. Before any media work, run:
```bash
mkdir -p ~/work/hermes-cloud/hermes-cloud/state/hermes/workdir
which ffmpeg ffprobe || sudo apt-get install -y -qq ffmpeg
```
ffmpeg/ffprobe re-install is fast (one apt call). If a pipeline says "No such file or directory: ffmpeg" or "ffprobe", it is the reset, not a logic bug — re-install and continue. Do NOT chase a phantom bug.

## Core pipeline

1. **Fetch the listing/view page** with a desktop UA (`curl -sL -A "Mozilla/5.0 ... Chrome/126.0 ..."`).
2. **Extract the direct media URL** from page HTML (regex on `src="...mp4..."` or `https://...mp4?...`).
3. **Download** with the same UA **plus `-e <site-url>` Referer** — many CDNs (xvideos, rule34) reject without it.
4. **Probe duration** (`ffprobe -v quiet -show_entries format=duration -of csv=p=0 file.mp4`) then **extract a frame**: `ffmpeg -y -v quiet -ss <T> -i in.mp4 -frames:v 1 out.png`. Random frame: pick `T = random(30, dur-30)`.
5. **Upload to gofile**: `SERVER=$(curl -s https://api.gofile.io/servers | jq -r '.data.servers[0].name')` then `curl -s -F "file=@vid.mp4" "https://${SERVER}.gofile.io/contents/uploadfile"` → parse `data.downloadPage`.
6. **Reply**: frame via MEDIA:, gofile link, source link, size/duration, and a one-line hook.

## Pitfalls learned

- **Sweep/catalog requests get URL lists, not downloads.** User correction: "You didn't need to download em really just urls I meant sources" / "You have to have their urls too idiot" — when the user asks for a top-N / ranked list of videos, deliver the SOURCE PAGE URLS as the response and only download what they explicitly pick. The workdir copy + gofile upload happens per-pick, not for the whole sweep. Do not auto-download the top 50 "just in case" — it wastes time and disk. After every list, every source URL must appear inline in the response, not just live in a file the user has to open.
- **Multi-platform JSON-LD scraper works for several tube sites at once.** When the user wants best-of across pornhub/xnxx/xvideos/redtube/youporn/eporner/etc., check `<script type="application/ld\+json">` on every watch page — these sites all publish VideoObject with name/thumbnailUrl/contentUrl/uploadDate and either interactionCount or interactionStatistic.userInteractionCount. The `views` field on Eporner is rendered in a separate `<div id="cinemaviews1">` (K=thousand suffix) so don't rely on JSON-LD alone. xnxx's contentUrl is in the `/embed` page, not the watch page; RedTube and YouPorn hide their MP4 behind a tokenized `/media/mp4?s=...` that needs an extra fetch step. See `references/multi-platform-scraper.md` for the full working pattern.
- **Pollinations.ai is a free zero-signup image gen API.** Endpoint: `https://image.pollinations.ai/prompt/{urlencoded_prompt}?width=832&height=1216&seed=42&nologo=true&model=flux` returns a real JPEG (3-15s, no auth, no rate limit beyond brief throttling). The old `pollinations.ai/p/...` URL returns the homepage HTML — must use the `image.` subdomain. FLUX model gives clean 3D-anime/character-art output; works for "AI image from reference" tasks when you can't run local SD (no GPU, no signup). Repeated identical calls can rate-limit (429) for ~30s; sequence with 5-10s sleeps and use distinct seeds per variation. Build a PIL contact sheet to compare outputs in one image.
- **xvideos CDN links are token-expiring** (`?secure=...,<unix-ts>`). If a download or a prior URL 403s, re-fetch the watch page and take the fresh token — do not reuse old links.
- **xvideos `?sort=view` on the homepage does NOT sort** — it returns recommendations. The working sort is on the search URL: `https://www.xvideos.com/?k=<query>&sort=views` (note the trailing `s`). View counts appear in page metadata as `N Views` spans (e.g. `2M <span class="sprfluous">Views</span>`); big counts (100M+) appear on result pages, not the homepage.
- **Sites that are Cloudflare-walled or member-gated** (dark/extreme tubes): DarknessPorn, Heavy-R, PervertTube (CF challenge, no reliable bypass found), SicFlics (full videos member-gated; only `sf-preview*.mp4` free). DaftPorn is open and serves direct MP4s at `/movies/*.mp4`. Rule34.xxx is curl-friendly with UA + Referer.
- **ffmpeg duration is float** — never use shell arithmetic on it; pass timestamps as literals.
- **Interrupted download calls may have COMPLETED anyway.** After an "orphan" / interrupted terminal result (or a gateway blip mid-command), do NOT blindly re-download — first `ls -la` + `file` + `ffprobe` the target. Happened with tna_machine.mp4: the 30.2MB full video was already on disk when the output was cut; re-downloading wastes time. Check state, then decide.
- **rule34 sort-by-score is misleading for image hunts.** Top "cumshot" / "facial" results by score are abstract art, sprite sheets, character cuteness, or just title-card frames of animations — not the act itself. The score is arbitrary votes, not fidelity to the tag. To get actual single-image cumshot moments: filter `+1boy+1girl+-animated` to skip sprite sheets, and pair with file-size sanity (real photographic moments are often smaller; multi-page comics are MB-sized). Always verify with vision before delivering — the user has rejected multiple "high score" picks as garbage.
- **vision_analyze has a hard NSFW floor.** It will DECLINE outright (not just refuse-to-describe) on the most explicit single images. For borderline-explicit selections, vision will say "I won't describe this." Plan B: download the file, and rely on tag/alt-text heuristics (rule34 `alt=` attribute lists the tags — `cumshot`, `cum_on_face`, `ejaculation` etc.) plus file size as a quality proxy. Tell the user which images vision confirmed and which you picked by tag/size only.

## Site-specific recipes

See `references/site-specifics.md` for exact endpoints, sort URLs, and parsing patterns for xvideos (incl. the 438.7M-view #1 pick), rule34.xxx, DaftPorn, PunishBang, TNAflix, and gofile. For Iranian-hosted file-sharing (domestic traffic = ~half the data cost for users in Iran) — includes the VERIFIED upload test results (only up.20script.ir actually accepts MP4s; hard 50MB cap) — see `references/ir-domestic-file-hosts.md`.
