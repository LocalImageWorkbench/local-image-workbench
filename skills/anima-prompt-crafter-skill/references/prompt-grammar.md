# Anima Prompt Grammar

## Default standard prompt

Use this shape unless the user asks for another format:

```text
Positive prompt
masterpiece, best quality, nsfw, rating_questionable, anime illustration, [subject tags], [composition tags], [setting tags], [style tags]. [Dense natural-language caption.]

Negative prompt
worst quality, low quality, lowres, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed, duplicate face, crossed eyes, messy lineart, watermark, signature, username, logo, unrelated text
```

Do not include aspect ratio or resolution. The workflow/node owns those.

## Tag style

- Use comma-separated tags before the prose caption.
- Prefer lower-case English tags.
- Preserve special forms such as `score_7`, `1girl`, `2boys`, or user-supplied LoRA trigger words.
- Use `@artist` only when supplied or requested.
- Avoid ten artist tags at once unless the task is explicit artist-mixing.
- Use concrete image tags over quality spam.

## Positive prompt layers

1. Quality and rating: `masterpiece, best quality, nsfw, rating_questionable, clean lineart` (use `safe, rating_safe` only for explicit SFW requests).
2. Subject count: `1girl`, `2characters`, `solo`, `group portrait`.
3. Identity and continuity: name, role, LoRA trigger, repeated character anchor.
4. Appearance: hair, eyes, face, body silhouette, outfit, accessories.
5. Pose and action: standing, sitting, running, casting spell, looking at viewer.
6. Composition: close-up, medium shot, full body, three-quarter view, low angle, symmetrical composition.
7. Setting: school rooftop, neon street, fantasy forest, studio backdrop.
8. Light and color: soft rim light, sunset backlight, cool blue shadows, pastel palette.
9. Rendering: anime illustration, cel shading, painterly anime, manga screentone, game CG, key visual.
10. Natural-language caption: one dense sentence that ties the scene together.

## Natural-language caption rules

The prose caption should read like a clear art-director brief:

- describe the final image, not the process;
- keep character details together;
- keep background details together;
- use spatial terms when placement matters;
- avoid alternatives such as "or", "maybe", "could be";
- avoid conflicting media.

## Mode recipes

### Base / quality route

Use detailed mixed prompts with complete subject, setting, lighting, and style. Good for final images, covers, character art, and benchmark baselines.

### Aesthetic / highres route

Emphasize key visual polish:

`anime key visual, refined composition, detailed background, polished cel shading, delicate lineart, cinematic color design`

Do not overload with random effects. Mention poster/cover/KV hierarchy when relevant.

### Turbo / Turbo LoRA route

Make the prompt simpler and more decisive. Use fewer competing details and clearer subject placement:

`1girl, full body, centered composition, school uniform, rooftop at sunset, clean anime lineart. A single character stands...`

### LoRA route

Place trigger words close to the relevant subject or style. Do not invent LoRA names. If the user provides a trigger, preserve it exactly. If multiple LoRAs are involved, separate their roles in prose:

`[character_trigger], 1girl, ...` for character identity.
`[style_trigger], anime illustration, ...` for visual style.

### Regional LLLite route

Use this output shape:

```text
Global prompt
[shared quality/style/world/lighting]

Red region
[subject or object in red mask, with left/right/foreground/background wording]

Blue region
[subject or object in blue mask...]

Green region
[background or prop region...]

Negative prompt
[global negatives plus regional failure negatives]
```

Regional color masks guide composition; they are not pixel-accurate cutouts. Mention color names only as region labels, not visible final colors, unless the mask color is actually meant to appear.

### Inpaint / repair route

Use this output shape:

```text
Whole image context
[brief description of the preserved image style, lighting, and character/world identity]

Masked area prompt
[the desired final appearance of only the repaired/repainted area]

Negative prompt
visible mask edge, patchy repair, mismatched lighting, mismatched style, bad anatomy, bad hands, extra fingers, deformed
```

Do not write "remove this" as the masked-area prompt. Write the final desired replacement.

### Character sheet route

Keep a stable identity anchor and vary only the requested view/expression/outfit:

```text
Character identity anchor
[name/role], [hair], [eyes], [outfit], [signature accessory], [body silhouette], [style anchor]

Prompt 01 - front view
[identity anchor], front view, neutral expression...
```

Negative prompt should include `inconsistent character, outfit mismatch, asymmetrical design error` when consistency matters.

### Storyboard / batch route

Repeat the character and style anchors in every prompt. Change only shot, action, emotion, and environment beat. Use numbered prompt pairs.

## Visible text

Anima can include short visible text but is not a typography-first model. If the user requests text:

- preserve the text exactly;
- describe it as a short sign/title/logo element in the prose;
- remove broad `text` negatives;
- keep `garbled text, misspelled text` only if preventing unreadable stray text.

## Negative prompt tuning

Start from the default negative and add only relevant terms:

- hands/body: `bad anatomy, bad hands, extra fingers, missing fingers, fused fingers, extra limbs`;
- face: `crossed eyes, asymmetrical eyes, duplicate face, distorted mouth`;
- regional: `merged characters, wrong region, duplicated character, object bleeding into other region`;
- inpaint: `visible mask edge, patchy repair, mismatched lighting, mismatched lineart`;
- output cleanliness: `watermark, signature, username, logo, unrelated text`.

Remove negatives that directly fight the requested output.

