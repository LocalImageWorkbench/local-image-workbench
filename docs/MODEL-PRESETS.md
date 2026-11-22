# 简洁模式推荐模型栈

目标：尽量少下载，一套底模覆盖 SFW 和 NSFW。

## 简洁底模卡片

应用现在提供五张卡片：Illustrious、MOSS、Krea2、Qwen 2.1、Anima。

推荐日常只装 Illustrious；需要成人向再加 MOSS。卡片切换只切换提示词目标和工作流，不会凭空补齐缺失的 UNET/CLIP/VAE。

## 最小推荐

| 用途 | 模型 | 大小参考 | 是否必须 |
|---|---|---|---|
| 提示词 | Ollama Qwen3.5 9B Abliterated | 本地已有 | 是 |
| 二次元出图 | Illustrious / WAI checkpoint | 约 6.6 GB | 是 |
| NSFW LoRA | 任意一个匹配 Illustrious/SDXL 的成人向 LoRA | 约 100–500 MB | NSFW 建议 |
| ComfyUI | 已安装 | 用户自备 | 是 |
| Ollama | 已安装 | 用户自备 | 是 |

一套底模同时覆盖：

- SFW：Illustrious 直出
- NSFW：Illustrious + 一个 NSFW LoRA

这比“SFW 用 Illustrious、NSFW 用 MOSS”少下一整套 MOSS 底模、文本编码器和 VAE。

## 可选，不默认安装

| 风格 | 底模 | 什么时候再装 |
|---|---|---|
| 写实 SFW | Krea2 或 Qwen-Image 2.1 | 需要照片感时 |
| 成人写实/高细节 | MOSS / PornMaster | Illustrious + LoRA 不够时 |
| Pony 生态 | Pony | 已有大量 Pony LoRA 时 |
| 其他 | Anima / SD1.5 | 明确需要对应 LoRA 时 |

不要为了“齐全”把五套底模全下载。

## LoRA 选择

- 必须与 Illustrious/SDXL 底模匹配。
- 先选 1 个 NSFW LoRA，确认效果后再加。
- 下载前看 Civitai 的 baseModel、文件大小、授权和是否付费。
- 没有匹配 LoRA 时简洁模式会直接底模出图，不阻塞。

## 风格下载推荐

| 想要 | 推荐 |
|---|---|
| 二次元、纯净 | Illustrious/WAI，无 LoRA |
| 二次元、成人 | Illustrious/WAI + 1 个 Illustrious NSFW LoRA |
| 电影感/摄影 | Krea2（SFW 优先） |
| 写实成人 | 先用 Illustrious+LoRA 测试；不满意再考虑 MOSS |
| 现成 Pony LoRA 很多 | Pony |

## 网络

直连 Civitai / Hugging Face 优先；CDN 失败时可测试 Ikuuu 等 VPN/梯子类工具，也可以自行使用同类产品。它们不是模型来源。
