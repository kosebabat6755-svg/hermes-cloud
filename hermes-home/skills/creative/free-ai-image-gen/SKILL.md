---
name: free-ai-image-gen
description: Pollinations FLUX free image gen, no signup needed.
---

# Free AI Image Generation (No Signup, No API Key)

Use this when the user needs AI-generated images and refuses (or cannot complete) signup on commercial platforms like Midjourney, DALL-E, NovelAI, Tensor.Art, or SeaArt. Also use when local GPU is unavailable (CPU-only VPS) and install/setup of ComfyUI/Automatic1111 is too heavy.

## Primary Endpoint: Pollinations.ai

**URL pattern:**
```
https://image.pollinations.ai/prompt/{url-encoded-prompt}?width=832&height=1216&seed=42&nologo=true&model={model}
```

- **No API key, no signup, no rate limit card** — IP-based soft throttling only
- **Returns**: `image/jpeg` direct response
- **Speed**: 3-15 seconds per image on first call, cached afterwards
- **Cost**: $0 — completely free, public service

**The OLD `pollinations.ai/p/...` endpoint returns HTML** (the marketing site). Always use `image.pollinations.ai/prompt/...`.

### Available Models (verified working 2026-09-05)

| Model name | What it is | Best for |
|---|---|---|
| `flux` | FLUX.1 default | Anime/3D/photoreal, NSFW allowed |
| `turbo` | Fast FLUX variant | Quick previews, lower quality |
| `sdxl` | Stable Diffusion XL | General purpose |
| `kandinsky` | Russian Kandinsky | Stylized art |
| **`nanobanana`** | **Gemini 2.5 Flash Image (Nano Banana v1)** | **Text-accurate, conversational editing** |
| **`nanobanana-2`** | **Gemini 3.1 Flash Image (Nano Banana 2)** | **Pro-quality at Flash speed, character consistency, 4K capable** |
| **`nanobanana-pro`** | **Gemini 3 Pro Image (Nano Banana Pro)** | **Highest quality, 1K/2K/4K output** |
| `gptimage` | Azure GPT Image 1 mini | OpenAI-style |
| `gptimage-large` | Azure GPT Image 1.5 | OpenAI-style, higher quality |

**The Nano Banana models are the killer feature**: Pollinations eats the Google Vertex AI cost and exposes them free. When the user asks for "Nano Banana" / "Gemini image gen" / "the best free image model", use `model=nanobanana-2` (or `nanobanana-pro` for top quality). Same URL pattern, just swap the `model=` value. Generation is slower than FLUX (25-45 sec vs 3-15 sec) and rate limits are tighter (3-5 sec spacing between calls) but quality is markedly better for character/portrait work.

**Why Pollinations is the only free anonymous Nano Banana 2 path:** Google's own API, Puter, OpenRouter, Together, LaoZhang, ilisai, Lovart, GenAIntel all require signup or paid credit. The model=`nanobanana-2` parameter on Pollinations is the only no-signup no-key option verified working from this VPS (others get CF-walled or return 401).

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
- **Add `time.sleep(5-8)` between calls** when batching >3 images on FLUX, **`time.sleep(3-5)` on Nano Banana models** (tighter rate limits but each call takes 25-45 sec anyway).
- **Each new image = new seed** if user wants variety. Re-using seed = re-generating same image (deterministic).
- **Image lifetime**: cached on Pollinations CDN for ~1 year per URL. Same prompt + same seed = same image, re-fetchable.

## Pitfalls

- **HTML response trap**: If you see `<!DOCTYPE` in the response body, you hit the marketing page endpoint. The image endpoint is `image.pollinations.ai` (not `pollinations.ai`).
- **Truncated downloads**: Some 200 responses return <5KB (rate-limited or model error). Always check `Content-Length` or file size.
- **Seed reuse for variation**: If user asks for "another angle" or "different pose", MUST change the seed. Same seed = same image.
- **vision_analyze on NSFW**: FLUX doesn't filter content; generated NSFW images can still be vision-analyzed, but some safety layers decline. Use sparingly.
- **Prompt length**: URLs >2000 chars break. Cap prompts at ~30 keyword terms.
- **Don't burn cycles searching for "free anonymous Nano Banana 2" endpoints**: The model=`nanobanana-2` parameter on `image.pollinations.ai` is the only no-signup path. Before spending time probing Puter/Google API/OpenRouter/etc for an anonymous Nano Banana endpoint, just hit Pollinations with `model=nanobanana-2` — works in 2-45 sec, valid JPEG, no auth. The dead-end services (Puter needs account, Google API needs key+billing, OpenRouter $0.05/img, GenAIntel needs email, Lovart CF-blocks Azure VPS, ilisai needs Google account) are not worth chasing.
- **Nano Banana prompt prefix**: Pollinations internally adds `Generate an image but only if the prompt and input images are safe. Else return an error: {your_prompt}` — so don't pre-prefix safety language; just write the image prompt directly.

## When NOT to Use This

- User has Midjourney/NovelAI/API budget AND wants highest quality AND is willing to pay → use those instead.
- User wants a specific LoRA / character-trained model → install ComfyUI locally with that LoRA.
- User wants image-to-image (upload reference + transform) → Pollinations doesn't support that natively; use a HuggingFace Space instead.
- User wants 4K output consistently → `nanobanana-pro` supports it but Pollinations caps at 1K by default; commercial Vertex API is needed for 2K/4K.

## Related Skills

- `web/blocked-page-recovery` — when free endpoints get CF-walled or rate-limited hard
- `media/web-video-harvest` — sibling for video, not images

## Verified Working (2026-09-04)

- Server: Azure VPS, x86_64, 8GB+ RAM, no GPU
- 832x1216 portrait images, FLUX model, 3-15 sec each
- 6/7 batch success rate with 8s spacing
- Generated teal/green-haired 3D anime rear views matching "yeero style" prompt; user's source reference was a 3D-animated Kiriko from rule34.xxx post 8132055
