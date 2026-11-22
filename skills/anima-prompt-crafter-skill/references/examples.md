# Anima Prompt Examples

## Sparse idea

Input: `银发少女，废墟城市，孤独感，Anima`

Output:

```text
Positive prompt
masterpiece, best quality, nsfw, rating_questionable, anime illustration, 1girl, solo, silver hair, long hair, blue eyes, black cloak, ruined city, overgrown concrete, melancholic atmosphere, wide shot, soft cel shading, detailed background, cool gray palette. A lonely silver-haired girl stands in the middle of an abandoned city avenue, her black cloak moving lightly in the wind, broken glass and moss-covered concrete around her, distant collapsed towers fading into pale morning haze, with clean anime lineart and quiet emotional storytelling.

Negative prompt
worst quality, low quality, lowres, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed, duplicate face, crossed eyes, messy lineart, watermark, signature, username, logo, unrelated text
```

## Multi-character cover

Input: `四人小队，奇幻冒险封面，主角在中间，其他三人围绕`

Output:

```text
Positive prompt
masterpiece, best quality, nsfw, rating_questionable, anime key visual, 4characters, fantasy adventuring party, centered hero, group composition, dramatic cover art, clean lineart, polished cel shading, detailed fantasy background. A fantasy adventure cover showing the young leader in the center foreground wearing a deep-blue travel coat and holding a glowing map, with a red-haired swordswoman on the left, a calm silver-haired mage on the right, and a small cheerful engineer behind them carrying a lantern. Ancient stone ruins and floating crystal fragments fill the background, warm golden light breaks through storm clouds, and the whole image feels like a polished anime game key visual with strong character hierarchy.

Negative prompt
worst quality, low quality, lowres, blurry, jpeg artifacts, bad anatomy, bad hands, extra fingers, missing fingers, extra limbs, deformed, duplicate face, merged characters, duplicated character, messy lineart, watermark, signature, username, logo, unrelated text
```

## Regional LLLite prompt

Input: `红区主角，蓝区反派，绿区城堡背景，黄区发光标题`

Output:

```text
Global prompt
masterpiece, best quality, nsfw, rating_questionable, anime key visual, fantasy duel poster, dramatic lighting, clean lineart, polished cel shading, detailed castle background, high contrast blue and gold palette.

Red region
The main heroine occupies the foreground center-left, a young knight with short white hair, blue eyes, a silver breastplate, and a torn red cape, holding a glowing sword forward with a determined expression.

Blue region
The antagonist occupies the right side and slightly higher background layer, a tall dark sorcerer in a black robe with violet magical smoke around one hand, looking down toward the heroine.

Green region
A ruined gothic castle fills the far background, with broken towers, moonlit stone arches, and drifting mist behind the two characters.

Yellow region
A short glowing fantasy title sits across the upper band, bright golden serif letters, readable and separated from the characters.

Negative prompt
worst quality, low quality, lowres, blurry, bad anatomy, bad hands, extra fingers, missing fingers, merged characters, wrong region, duplicated character, object bleeding into other region, messy lineart, watermark, signature, username, logo
```

## Inpaint repair prompt

Input: `修手，保持原来的二次元风格和衣服`

Output:

```text
Whole image context
anime illustration, clean lineart, soft cel shading, the original character identity, outfit colors, lighting direction, background, and overall art style are preserved.

Masked area prompt
a natural five-finger human hand with correct anime anatomy, slender fingers, clean knuckles, relaxed pose, matching skin tone, matching cel-shaded highlights, sleeve cuff aligned naturally with the wrist.

Negative prompt
visible mask edge, patchy repair, mismatched lighting, mismatched style, bad anatomy, bad hands, extra fingers, missing fingers, fused fingers, deformed fingers, distorted wrist, messy lineart
```

## Character sheet

Input: `做一个蓝发魔法少女角色设定提示词`

Output:

```text
Character identity anchor
masterpiece, best quality, nsfw, rating_questionable, anime character sheet, magical girl, 1girl, bright blue twin-tail hair, star-shaped hair clips, violet eyes, white and navy magical dress, crescent-moon brooch, short cape, knee-high boots, cheerful but brave expression, clean lineart, soft cel shading, simple light-gray studio background.

Prompt 01 - front view
masterpiece, best quality, nsfw, rating_questionable, anime character sheet, front view, full body, bright blue twin-tail magical girl with star hair clips, violet eyes, white and navy magical dress, crescent-moon brooch, short cape, knee-high boots, standing neutrally with arms relaxed, clean lineart, soft cel shading, simple light-gray studio background.

Prompt 02 - side view
masterpiece, best quality, nsfw, rating_questionable, anime character sheet, side view, full body, same bright blue twin-tail magical girl, the short cape and crescent brooch remain visible in profile, boots and skirt silhouette clearly readable, clean lineart, soft cel shading, simple light-gray studio background.

Negative prompt
worst quality, low quality, lowres, blurry, bad anatomy, bad hands, extra fingers, missing fingers, inconsistent character, outfit mismatch, asymmetrical design error, deformed, messy lineart, watermark, signature, username, logo, unrelated text
```

