# Pollinations.ai image generation — API reference

The canonical image-gen endpoint that's free, no-signup, and unfiltered enough for the 3D-MMD tier.

## Endpoints (don't confuse them)

- `https://pollinations.ai/p/<prompt>` — **HTML webpage**, NOT the image. Will look like a 200 with 4-5KB of HTML.
- `https://image.pollinations.ai/prompt/<prompt>` — **the actual image** (image/jpeg). This is the one to use.

Always hit the second. First-time mistakes cost a real call to discover the swap.

## Request shape

```
GET https://image.pollinations.ai/prompt/{url-encoded-prompt}?width=<W>&height=<H>&seed=<N>&nologo=true&model=flux
```

Query params that matter:
- `width` × `height` — common 832x1216 (portrait, anime-friendly), 1024x1024 (square)
- `seed` — integer, any value; different seeds = different variations. Increment by 100-200 per variation.
- `nologo` — `true` strips watermark
- `model` — `flux` is the best quality free default. Other options include `flux-pro`, `turbo`, `sdxl` but flux is the safe pick for this user's style.

No API key. No auth header. No signup. No rate-limit header in response.

## Response shape

- 200 + `content-type: image/jpeg` on success — typical 30-50KB for 832x1216
- 429 when rate-limited — 800-1200 bytes, very fast (<1s)
- 200 + 4-5KB of HTML = wrong endpoint (you hit the webpage)
- Response has `cache-control: public, max-age=31536000, immutable` — image URLs are CDN-cached and reusable

## Rate limits (observed)

- Sequential with `time.sleep(5-8)` between calls: ~6/7 success rate, occasional 429
- Concurrent (ThreadPoolExecutor with 3+ workers): mostly 429s
- Per-IP throttle; not documented but the 5-8s spacing is reliable

## Model behavior

FLUX follows the prompt closely but is NOT fine-tuned for any specific 3D-MMD artist. The pattern that gets the closest to YEERO / POLISHED-JADE-BELL / TYPANIA style:

```
<artist> style 3d anime <character> <angle> <pose> <hair> <outfit> <setting> <lighting> masterpiece best quality
```

- `3d anime` or `3d mmd` — non-negotiable for this user's tier
- Artist name (`yeero`, `polished jade bell`, `typania`) — weak signal alone, strong combined with style keywords
- Cyberpunk / neon / glossy / watermarked keywords for the YEERO/cyberpunk subset
- `masterpiece, best quality` — common Danbooru/SDA tags, FLUX responds well

Negative prompts: Pollinations FLUX does not support negative prompts on the free endpoint. Work around by being positive about what you DO want.

## Working prompts (verified)

**YEERO Kiriko rear shot, cyan-lit, crouching, 3D anime:**
```
3d anime style cyberpunk cyan teal neon lighting 1girl from behind close up rear view green hair ponytail red bodysuit dark thighhighs striped stockings crouching pose low angle atmospheric teal rim lighting masterpiece best quality yeero style
```

**Overwatch rear shot, walking-away pose:**
```
3d anime cyberpunk cyan neon lighting futuristic corridor 1girl solo from behind straight on full body wide shot green hair ponytail red bodysuit dark thighhighs standing arched back looking back over shoulder masterpiece best quality cinematic lighting yeero
```

**Variation, bent-over pose:**
```
3d anime style cyberpunk cyan teal neon lighting 1girl from behind bent over rear view green hair ponytail pink bow red bodysuit dark thighhighs striped stockings depth of field masterpiece best quality yeero
```

## Delivery pattern

After 4-6 generations, build a contact sheet with ffmpeg (see main SKILL.md for the filter graph), `vision_analyze` the SHEET, send the best one inline via MEDIA:, full sheet inline, source URL. Never send individual files one-by-one — user wants to pick from a grid.

## Pitfalls

- **HTML endpoint confusion** — `pollinations.ai` vs `image.pollinations.ai` is the #1 mistake. First call should always verify content-type is image/jpeg, not text/html.
- **Empty responses** — 429s come back as small responses, not empty. Check `size_download > 5000` before trusting.
- **No negative prompts** — describe what you want, not what you don't.
- **FLUX is slow vs SDXL-Turbo** — 3-15s per image is normal. Don't increase timeout beyond 60s.
- **First call may take 15-20s** — model cold start. Subsequent calls faster.
