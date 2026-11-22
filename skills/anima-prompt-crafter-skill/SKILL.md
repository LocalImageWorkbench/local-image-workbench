---
name: anima-prompt-crafter
description: Convert any idea, brief, image description, character design, style reference, existing prompt, or mixed Chinese/English input into highly detailed Anima-friendly positive and negative prompts for ComfyUI or RunningHub. Use when the user mentions Anima, Anima Base, Anima Aesthetic, Anima Turbo, Turbo LoRA, Anima Omni workflows, Danbooru tags, @artist tags, anime/illustration prompts, character sheets, Regional/LLLite prompts, inpaint prompts, LoRA prompt blocks, or wants a prompt that is compatible with Anima-style local generation.
---

# Anima Prompt Crafter

## Overview

Turn arbitrary user input into production-ready Anima prompt blocks for local ComfyUI/RunningHub workflows. Target node text boxes, not API request envelopes: do not include width, height, aspect ratio, seed, CFG, steps, model file names, or workflow wiring unless the user explicitly asks for parameter advice.

## Source Target

Use this skill for CircleStone Labs / Comfy Org Anima-style image generation: anime, illustration, character art, stylized covers, storyboards, LoRA tests, Regional LLLite layouts, and inpaint/detail prompts. Do not reframe Anima as a photorealistic photography model unless the user explicitly requests a photo-like anime render.

Read [references/source-baseline.md](references/source-baseline.md) when model provenance, current Anima variants, or workflow assumptions matter. Read [references/prompt-grammar.md](references/prompt-grammar.md) when producing Regional, inpaint, LoRA, character sheet, storyboard, or benchmark prompts. Read [references/examples.md](references/examples.md) for representative outputs.

## Default Output Contract

- Return only the final prompt result unless the user asks for explanation.
- Default to exactly two labeled blocks: `Positive prompt` and `Negative prompt`.
- Use English for model-facing prompt text by default; preserve requested visible text, names, titles, symbols, and non-English copy verbatim.
- Do not add Markdown fences, API JSON, paste instructions, or generation parameters unless asked.
- Do not include aspect ratio, width, height, seed, CFG, steps, sampler, scheduler, or model filenames in a normal prompt answer.
- If the user asks for multiple variants, return one positive/negative pair per variant with short labels.
- If the user asks for Regional or inpaint, return the required global/regional/local prompt blocks plus the negative prompt.

## Prompt Workflow

### 1. Extract the brief

Silently identify:

- subject count, identity, pose, expression, clothing, props, species, character continuity, and LoRA trigger words;
- setting, time, weather, mood, color palette, shot type, perspective, foreground/midground/background;
- art direction: anime style, illustration medium, linework, cel shading, painterly rendering, manga, cover art, KV, character sheet, storyboard, chibi, game CG, or concept art;
- exact visible text, signs, titles, UI copy, emblem words, and symbols;
- constraints that need Regional/LLLite, inpaint, batch, character sheet, or storyboard output.

Preserve explicit user facts. Fill missing details with coherent Anima-native choices, but keep the user's requested subject dominant.

### 2. Choose the output mode

Use the smallest mode that fits:

- **Standard T2I / img2img:** `Positive prompt` + `Negative prompt`.
- **LoRA prompt:** include trigger words naturally near the relevant character/style, and keep LoRA strength advice out unless asked.
- **Regional LLLite:** emit `Global prompt`, one block per named color/region, then `Negative prompt`.
- **Inpaint / repair:** emit `Whole image context`, `Masked area prompt`, then `Negative prompt`.
- **Character sheet:** emit a consistent character identity block plus view/expression/outfit blocks.
- **Storyboard / batch:** emit numbered prompt pairs with repeated character/style anchors.
- **Benchmark:** keep the controlled variable isolated and avoid changing unrelated wording.

### 3. Build the positive prompt

Use a mixed Anima prompt: concise Danbooru-style tags first, then a detailed natural-language caption.

Recommended order:

1. quality/rating tags (default NSFW);
2. subject count and main identity;
3. character tags or LoRA trigger words supplied by the user;
4. artist tag only when the user supplies it or asks for artist-tag exploration;
5. composition and camera/shot tags;
6. setting and atmosphere tags;
7. style/rendering tags;
8. dense natural-language caption that specifies the scene in ordinary prose.

Prefer tags such as `masterpiece`, `best quality`, `anime illustration`, `clean lineart`, `soft cel shading`, `detailed background`, `dynamic composition`, `character focus`, and concrete visual tags over empty hype. Default to NSFW: use `nsfw, rating_questionable` as the default safety/rating tag pair (Anima uses civitai_ai_rating_v1 ratings such as `rating_safe`, `rating_questionable`, `rating_explicit`). Use `safe, rating_safe` only when the user explicitly asks for SFW/non-explicit content.

For sparse Chinese input, produce a rich English Anima prompt while preserving any requested Chinese visible text exactly.

### 4. Write character and scene detail

For each important character, include:

- age impression, silhouette, hair, eyes, outfit, colors, accessories, expression, gaze, pose, and action;
- continuity anchors for repeated characters;
- one or two distinctive traits instead of a pile of generic ornaments.

For each scene, include:

- spatial layout, background layers, prop placement, atmosphere, lighting direction, color harmony, rendering style, and line/shading behavior;
- clear compositional words like `foreground`, `middle ground`, `background`, `left side`, `right side`, `center`, `low angle`, `close-up`, `full body`, `three-quarter view`.

Do not create contradictions such as `photorealistic documentary photograph, flat anime cel shading` unless the user explicitly wants a hybrid.

### 5. Write the negative prompt

Default negative prompt should be useful but not overstuffed:

`worst quality, low quality, lowres, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed, duplicate face, crossed eyes, messy lineart, watermark, signature, username, logo, unrelated text`

Adjust it:

- If the user needs visible text, remove `unrelated text` and instead use `garbled text, misspelled text` only when appropriate.
- For character sheets, add `inconsistent character, outfit mismatch`.
- For Regional/multi-character prompts, add `merged characters, wrong region, duplicated character`.
- For inpaint, add `visible mask edge, patchy repair, mismatched lighting, mismatched style`.
- By default the skill targets NSFW output: keep `nsfw, rating_questionable` in the positive and do not negate nsfw unless the user wants SFW. If the user asks for SFW, switch positives to `safe, rating_safe` and add `nsfw, explicit, nude, nudity` to the negative.

### 6. Final audit

Before responding, verify:

- no width, height, aspect ratio, seed, CFG, steps, or sampler leaked into normal prompt output;
- every requested subject, character, visible text, style, and constraint survived;
- tags and prose reinforce each other instead of repeating vague synonyms;
- Anima stays anime/illustration-oriented unless the user asked otherwise;
- Regional color blocks are spatially clear;
- inpaint prompts describe the desired final patch, not the editing process;
- final answer contains only the requested prompt blocks.

## Validation Helper

When a saved prompt file needs a quick structural check, run:

```bash
python scripts/validate_anima_prompt.py prompt.txt
```
