# Anima Source Baseline

## Official source snapshot

- Hugging Face model card: https://huggingface.co/circlestone-labs/Anima
- Hugging Face README source: https://huggingface.co/circlestone-labs/Anima/blob/main/README.md
- Comfy Org Anima tutorial: https://docs.comfy.org/tutorials/image/anima/anima
- Comfy Org changelog: https://docs.comfy.org/changelog

Treat these as the external baseline when current behavior matters. Anima is presented as a text-to-image model for anime/non-realistic art generation, with Anima-Base, Anima-Aesthetic, and Anima-Turbo variants in the official model card. The card says prompts can use Danbooru tags, natural language, or both.

## Local workflow baseline from the user's Anima Omni notes

The user's local Anima workflow direction emphasizes:

- Anima-Base v1.0 remains the stable core for the local workflow pack.
- Fast local generation is usually handled through Turbo LoRA in the user's RunningHub/ComfyUI workflow context, even though official sources also list an Anima-Turbo variant.
- Anima is best framed as anime, illustration, character art, and non-photorealistic art.
- Prompt systems must support Danbooru-style tags, natural language, artist tags, quality tags, and mixed prompts.
- Artist tags may use `@artist` format when the workflow/user requests artist-tag exploration.
- LoRA workflows may distinguish MODEL strength and TE strength; do not include strength numbers in pure prompt output unless requested.
- Regional LLLite is an important composition-control mode. Prompt blocks should explicitly state left/right/foreground/background or named color regions.
- Inpaint prompts should describe the whole image context and the desired masked-area result.
- Control-chain order in workflow docs: Regional first, then AnyTest/Pose/Lineart/Depth/Scribble, then Inpaint/Repair, then sampling, then Detail/Tile/Upscale.

## Prompt implications

- Default to Anima-native illustrated language, not DSLR realism.
- Prefer mixed tag + prose prompts over only prose for precision.
- Keep exact user-supplied visible text verbatim, but avoid promising perfect typography; Anima is not a typography-first model.
- Do not put workflow settings, model filenames, aspect ratio, resolution, sampler, steps, CFG, or seed inside normal prompt output.
- If a user asks for model setup advice, keep it in a separate `Suggested settings` section.

