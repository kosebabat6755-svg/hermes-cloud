---
name: rule34-3d-anime-harvest
description: 3D-anime rule34 + AI angle variations.
---

# 3D-Animated Anime Character Workflow (rule34.xxx → Pollinations AI)

Use when the user wants 3D-animated NSFW anime characters in a specific artist's style, especially the "modern 3D MMD" tier (YEERO, POLISHED-JADE-BELL, TYPANIA, NUTTYCRAVAT, SLAYED.COM, PureEvilCorp, Mikayori). Also use when user has a reference image and wants AI-generated variations from a different angle/pose.

## Class of character this is for

The user specifically collects the "3D MMD-style animated" tier of rule34 content — distinctly different from 2D hand-drawn anime, photoreal CGI, or live-action cosplay. Common signals:
- Source: rule34.xxx, gelbooru (`3d_mmd` tag), pixiv (MMD tag)
- Artist names: YEERO, POLISHED-JADE-BELL, TYPANIA, NUTTYCRAVAT, SLAYED.COM, PureEvilCorp, Mikayori
- Style cues: glossy 3D render, cel-shaded, cyberpunk or sci-fi settings, NEON lighting, often NSFW
- Recurring chars: Overwatch (Kiriko, Tracer, D.Va, Widowmaker, Mercy), Genshin, Honkai

When user says "the 3D animated ones" / "MMM-D" / "the good ones" / "the kiriko from that video" / names a YEERO-style artist, this is the skill.

## Source harvesting (rule34.xxx)

### Search endpoints that work
```
https://rule34.xxx/index.php?page=post&s=list&tags=<artist>_<name>+sort:score
https://rule34.xxx/index.php?page=post&s=list&tags=<character>_(source)+sort:score
https://rule34.xxx/index.php?page=post&s=list&tags=3d_mmd+<character>+sort:score
https://rule34.xxx/index.php?page=post&s=list&tags=<artist>_<name>+from_behind+sort:score
```

Sort by `score` for highest-rated. `from_behind` is a common ask but many great rear shots aren't angle-tagged — the unfiltered artist search often beats the angle filter.

### ID-first harvesting
- Listing gives `id` but NOT the real file path
- Real file URL only resolvable via browser DOM inspection — sample URL pattern from listing (`/samples/X/sample_HASH.jpg`) is WRONG
- Real pattern is `https://wimg.rule34.xxx//images/<DIR>/<HASH>.<ext>?<PID>` (note double-slash and `/images/` not `/samples/`, no `sample_` prefix)
- DIR can only be discovered by visiting the post page itself

### Two-step fetch (always)
1. `browser_navigate` to the post page
2. `browser_console` extract: `document.querySelector('img[src*="wimg.rule34.xxx"]')?.src` → real image URL
3. `curl -L` that URL directly to workdir

For .mp4 posts (animated 3D content): same browser, look for `document.querySelector('video')` → `currentSrc` or `src` attribute on `<source>` element. The .mp4 URL also follows the `/images/<DIR>/<HASH>.mp4?PID` pattern.

### Batch download pattern
For multi-ID harvests, run `curl` requests serially (10-20s each) — rule34 rate-limits bursts. Use a small Python loop with `sp.run` and `time.sleep(1-2)` between IDs. Parallel fetch will get 403/17B/404.

## Generating AI variations from a reference image

When user has a specific reference image (a frame from a video, a downloaded still, etc.) and wants a different angle/pose:

### Use Pollinations.ai (free, no signup)
```
https://image.pollinations.ai/prompt/{url-encoded-prompt}?width=832&height=1216&seed=N&nologo=true&model=flux
```

**Working prompt that nailed the rear Kiriko from the user's YEERO ref (verified 2026-09-04):**
```
yeero style 3d anime girl crouching from behind low angle green hair ponytail pink bow red bodysuit dark striped thighhighs cyberpunk cyan neon corridor yeero watermark 3d rendered masterpiece best quality
```

**Generalized template** (swap character details):
```
<artist> style 3d anime <character> from <angle> <pose> <hair color> hair <hair style> <outfit> <setting> <lighting> masterpiece best quality
```

**Sequential not parallel** — Pollinations soft-throttles per-IP on concurrent requests. Add `time.sleep(5-8)` between calls. Each variation = new seed.

See `creative/free-ai-image-gen` skill for full Pollinations workflow, model options, and rate-limit behavior. The free-ai-image-gen skill is the canonical place for the API details; this skill is the routing/decision tree for when to use it.

## Source → AI-variation pipeline (canonical workflow)

1. User requests "more of X character in Y style" or "different angle of this image" or "from behind"
2. Identify the artist's house style (3D, cyberpunk, neon, glossy). Confirm by inspecting the reference.
3. Find 5-10 source images via rule34 artist search → batch fetch into workdir
4. If user wants AI gen: send the best reference to vision_analyze to extract character features (hair, outfit, color, setting) — accept that some NSFW refs get declined, fall back to user description
5. Build Pollinations prompt from extracted features + user's requested angle
6. Generate 3-6 variations with different seeds, save to workdir
7. Deliver: source images inline via MEDIA: + AI generations inline + source URLs + gofile link if user wants the full set

## When to ask user vs just generate

- **Just generate** (4-6 variations, different seeds + angles): when user said "find me more" or "another angle" or "different pose" or "just do it idgaf"
- **Ask first (one question max)**: when user wants a specific angle/pose/character that wasn't in the original

## Pitfalls

- **rule34 sample URL is wrong**: listing page shows `/samples/X/sample_HASH.jpg` but file is at `/images/X/HASH.jpg?PID` (no `sample_` prefix, `/images/` not `/samples/`, double-slash). Always use browser_console to get the real URL.
- **Image hash truncation in listings**: some listings have truncated hashes in the HTML. Use the post page DOM, not the listing HTML.
- **"from_behind" tag narrows, doesn't find best**: the BEST rear shot is often untagged. Always do both: tag-filtered search + unfiltered artist search.
- **Pollinations soft rate-limit**: 6/7 success rate with 8s spacing. Concurrent = 429.
- **vision_analyze declines NSFW**: 3D rear shots often trip vision's safety. Fall back to extracting features from the source image's filename/title and user description.
- **FLUX default is not 3D-MMD-specialized**: For tighter stylistic match, prompt must explicitly include "3d anime", the artist name, and key style cues (cyberpunk, neon, glossy, watermark). Artist name alone is a weak signal.
- **Recurring character ≠ recurring style**: Kiriko has thousands of posts. Filter by artist tag for the specific style the user wants.
- **"from_behind" + Kiriko returns too much**: rule34's `from_behind` filter on a popular character returns hundreds. Cap at top 10 by score; user picks from the contact sheet.

## Verified workflow (2026-09-04)

User wanted YEERO Kiriko from rule34 post 8132055 → all rule34 listing URLs returned generic, unfiltered results. Found the rear shot by browsing the post page DOM and extracting the actual `wimg.rule34.xxx` URL. Generated 6 Pollinations variations (3-15s each) — all matched the YEERO cyberpunk cyan-lit rear-shot style. User said "Good shit" and immediately pivoted to MT4 setup.
