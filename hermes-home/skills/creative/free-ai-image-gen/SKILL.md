---
name: free-ai-image-gen
description: Pollinations FLUX free image gen, no signup needed.
---

# Free AI Image Generation (No Signup, No API Key)

Use this when the user needs AI-generated images and refuses (or cannot complete) signup on commercial platforms like Midjourney, DALL-E, NovelAI, Tensor.Art, or SeaArt. Also use when local GPU is unavailable (CPU-only VPS) and install/setup of ComfyUI/Automatic1111 is too heavy.

## Primary Endpoint: Pollinations.ai

**URL pattern:**
```
https://image.pollinations.ai/prompt/{url-encoded-prompt}?width=832&height=1216&seed=42&nologo=true&model=flux
```

- **Model options**: `flux` (default, high quality), `turbo` (faster, lower quality), `sdxl`, `kandinsky`
- **No API key, no signup, no rate limit card** — IP-based soft throttling only
- **Returns**: `image/jpeg` direct response
- **Speed**: 3-15 seconds per image on first call (FLUX), cached afterwards
- **Cost**: $0 — completely free, public service

**The OLD `pollinations.ai/p/...` endpoint returns HTML** (the marketing site). Always use `image.pollinations.ai/prompt/...`.

## Quick Win Workflow

1. Encode prompt with `urllib.parse.quote()`
2. `curl -sL -m 180 -o output.jpg "https://image.pollinations.ai/prompt/{encoded}?width=832&height=1216&seed=42&nologo=true&model=flux"`
3. Verify first bytes are `\xff\xd8` (JPEG magic) before declaring success
4. If `< 5KB` returned, treat as error/rate-limit and retry with `time.sleep(5-10)` + new seed

## Prompt Recipes for Common User Requests

**Anime/3D character rear angle** (the canonical use case that worked):
```
yeero style 3d anime girl crouching from behind low angle green hair ponytail pink bow red bodysuit dark striped thighhighs cyberpunk cyan neon corridor yeero watermark 3d rendered masterpiece best quality
```

**Anime 2D character portrait:**
```
masterpiece, best quality, 1girl, solo, anime, [hair color] hair, [eye color] eyes, [outfit], [pose], looking at viewer, simple background
```

**Negative terms to avoid in prompt** (FLUX doesn't have native negative prompts, but these work as exclusions in prefix): `lowres, bad anatomy, extra fingers, blurry, watermark, text, censored`

**Photoreal portrait:**
```
photorealistic, 8k, professional photography, [subject], [lighting], [lens], depth of field, sharp focus
```

## Pacing & Retry Discipline

- **Sequential, not parallel** — Pollinations soft-throttles per-IP on concurrent requests; one HTTP 429 every few seconds.
- **Add `time.sleep(5-8)` between calls** when batching >3 images.
- **Each new image = new seed** if user wants variety. Re-using seed = re-generating same image (deterministic).
- **Image lifetime**: cached on Pollinations CDN for ~1 year per URL. Same prompt + same seed = same image, re-fetchable.

## Pitfalls

- **HTML response trap**: If you see `<!DOCTYPE` in the response body, you hit the marketing page endpoint. The image endpoint is `image.pollinations.ai` (not `pollinations.ai`).
- **Truncated downloads**: Some 200 responses return <5KB (rate-limited or model error). Always check `Content-Length` or file size.
- **Seed reuse for variation**: If user asks for "another angle" or "different pose", MUST change the seed. Same seed = same image.
- **vision_analyze on NSFW**: FLUX doesn't filter content; generated NSFW images can still be vision-analyzed, but some safety layers decline. Use sparingly.
- **Prompt length**: URLs >2000 chars break. Cap prompts at ~30 keyword terms.

## When NOT to Use This

- User has Midjourney/NovelAI/API budget and wants highest quality → use those instead.
- User wants a specific LoRA / character-trained model → install ComfyUI locally with that LoRA.
- User wants image-to-image (upload reference + transform) → Pollinations doesn't support that natively; use a HuggingFace Space instead.

## Related Skills

- `web/blocked-page-recovery` — when free endpoints get CF-walled or rate-limited hard
- `media/web-video-harvest` — sibling for video, not images

## Verified Working (2026-09-04)

- Server: Azure VPS, x86_64, 8GB+ RAM, no GPU
- 832x1216 portrait images, FLUX model, 3-15 sec each
- 6/7 batch success rate with 8s spacing
- Generated teal/green-haired 3D anime rear views matching "yeero style" prompt; user's source reference was a 3D-animated Kiriko from rule34.xxx post 8132055
