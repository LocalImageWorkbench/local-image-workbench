# Anima Prompt Crafter

Anima Prompt Crafter is a Codex skill for turning rough ideas, Chinese or English briefs, character notes, style references, and existing prompts into production-ready Anima prompt blocks for ComfyUI and RunningHub workflows.

It is designed for anime, illustration, character art, fantasy scenes, concept fashion, LoRA tests, Regional LLLite composition prompts, and inpaint or repair prompts.

## What It Does

- Converts sparse ideas into detailed Anima-friendly prompt text.
- Uses a mixed prompt style: concise Danbooru-style tags first, followed by a dense natural-language art direction caption.
- Returns clean prompt blocks such as `Positive prompt` and `Negative prompt`.
- Preserves user-supplied names, visible text, symbols, LoRA trigger words, and style anchors.
- Supports standard T2I/img2img prompts, LoRA prompt blocks, Regional LLLite blocks, inpaint prompts, character sheets, storyboards, and benchmark variants.

## What It Avoids

This skill targets prompt text boxes, not workflow configuration. By default it does not include:

- width or height
- aspect ratio
- seed
- CFG
- steps
- sampler or scheduler
- model filenames
- workflow wiring

Those settings belong in the ComfyUI or RunningHub workflow, not inside the prompt itself.

## Output Shape

Default output:

```text
Positive prompt
masterpiece, best quality, nsfw, rating_questionable, anime illustration, clean lineart, soft cel shading, detailed background. ...

Negative prompt
worst quality, low quality, lowres, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed, duplicate face, crossed eyes, messy lineart, watermark, signature, username, logo, unrelated text
```

Regional and inpaint requests use specialized block structures described in `references/prompt-grammar.md`.

## Included Files

- `SKILL.md` - main skill instructions and routing rules.
- `references/source-baseline.md` - Anima model and local workflow assumptions.
- `references/prompt-grammar.md` - prompt formats for standard, LoRA, Regional LLLite, inpaint, character sheet, storyboard, and benchmark modes.
- `references/examples.md` - representative inputs and outputs.
- `scripts/validate_anima_prompt.py` - lightweight structural checker for saved prompt text files.
- `agents/openai.yaml` - optional agent metadata.

## Install

Copy this repository folder into your Codex skills directory:

```powershell
Copy-Item -Recurse . "$env:CODEX_HOME/skills/anima-prompt-crafter"
```

After installation, start a new Codex turn and ask for Anima, ComfyUI, RunningHub, anime illustration, Danbooru tag, Regional LLLite, LoRA, inpaint, or character-sheet prompts.

## 中文说明

这个技能用于把零散创意、中文/英文描述、角色设定、参考风格或已有提示词，整理成适合 Anima / ComfyUI / RunningHub 的正向与反向提示词。

核心目标不是堆参数，而是把画面主体、构图、材质、光线、风格、角色细节和反向约束写清楚。默认输出可直接复制到提示词节点中。
