# 模型指南

这是选型建议，不是效果保证。硬限制始终是：仅 18+ 虚构角色，禁止未成年、幼态、年龄不明，禁止真实人物性化。

工作台的 NSFW 开关只影响 LLM 写提示词，不会自动解锁画图模型。画图能否成人向取决于底模、LoRA、工作流和显存。

## LLM 模型

| 模型 | NSFW | 说明 |
|---|---|---|
| Ollama Qwen3.5 9B Abliterated | 可用 | 本地、速度快，复杂长提示词能力有限 |
| Ollama Qwen3.8 27B Abliterated | 可用 | 本地、质量更好，显存/速度压力更大 |
| OpenAI 兼容 + 本地无审查模型 | 取决于模型 | LM Studio/vLLM/llama.cpp 是否允许成人内容由模型本身决定 |
| Strata / 自定义本地网关 | 取决于底层模型 | 若提供 OpenAI 兼容接口即可接；内容能力看模型和模板 |
| OpenAI / Anthropic / Gemini 等云端 | 通常 SFW only | 多数会拒绝成人向请求，不要当 NSFW 模型使用 |
| OpenRouter 等聚合服务 | 取决于供应商 | 同一模型不同 provider 政策可能不同 |

推荐：

- 简洁默认：只装 Illustrious/WAI；SFW 直出，NSFW 加一个匹配 LoRA。
- 本地 NSFW 提示词：9B 用于快速草稿，27B 用于复杂场景。
- 云端：默认按 SFW 使用，除非你确认供应商和模型条款允许成人内容。

## 画图模型

| 底模 | NSFW | 说明 |
|---|---|---|
| MOSS / PornMaster | 可用 | 成人向首选，仍需成年虚构角色 |
| Illustrious / WAI | 可用/需 LoRA | 二次元稳定，解剖与风格可用 LoRA 提升 |
| Pony | 可用/需 LoRA | 成人向生态常见，必须使用成年角色 |
| SD1.5 anime checkpoint | 可用/需 LoRA | 老生态，模型和 LoRA 质量差异大 |
| Krea2 | SFW 优先/需测试 | 摄影感强，NSFW 不是主路线 |
| Qwen-Image 2.1 | SFW 优先 | 通用/写实强，成人向不保证 |
| Anima | 需 LoRA/测试 | 二次元模型，成人向需额外适配 |

## 推荐组合

SFW 通用：Qwen 2.1 或 Krea2 + 9B LLM。

成人向二次元：Illustrious/WAI 或 MOSS + 9B/27B。

成人向写实：MOSS + 适配 LoRA，先做小尺寸测试。

只有一个工作流时：空工作流 + 自动选 LoRA，再按提示词选底模。
