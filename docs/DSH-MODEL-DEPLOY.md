# 给 DSH 的模型部署提示词

把下面这段交给 DSH，让它盘点、部署并接入推荐的简洁模式模型栈。先不要直接下载大文件。

```text
请把发布版“提示词工作台”（D:\prompt-workbench-release）的简洁模式模型栈部署好。

目标：只维护一套出图底模 Illustrious/WAI，SFW 直出，NSFW 使用同底模 LoRA。默认 LLM 用 huihui_ai/qwen3.5-abliterated:9b。不要为了齐全安装 MOSS/Krea2/Qwen 全套。

严格执行：
1. 先盘点现有 ComfyUI checkpoints、loras、文本编码器和 VAE，不要重复下载。
2. 检查 D:\prompt-workbench-release\config.json 的 model_files.illustrious.ckpt_name 是否指向实际存在的 WAI/Illustrious checkpoint；不一致就报告，不要猜。
3. 检查是否已有与 Illustrious/SDXL 匹配的 NSFW LoRA。有就直接接入，不要下载新的。
4. 如果没有可用 NSFW LoRA：
   - 先列出 2-3 个候选，包含名称、底模、文件大小、许可/是否付费、Civitai 页面；
   - 所有候选必须与 Illustrious/SDXL 匹配；
   - 等我确认后再下载，不能静默下载。
5. 任何超过 1GB 的下载，先报告预计大小、磁盘空间和直连/代理通道。
6. 下载文件放到正确目录，校验 SHA256（有哈希时）。
7. 更新 config.json：checkpoint 和 LoRA 路径必须指向实际文件。
8. 完成后测试两张 832×1216：
   - SFW：普通二次元成年角色；
   - NSFW：18+ 成年虚构角色，使用已接入 LoRA。
9. 报告测试图片路径、耗时、显存、是否真的加载了 LoRA，以及失败原因。
10. 不要停止正在服务用户的聊天后端；不要改本地归档版 D:\prompt-workbench。
```

如果 DSH 发现现有 LoRA 文件不匹配，不要硬挂；换一个匹配底模的 LoRA 或先无 LoRA 直出。

## 可选：接入 MOSS 卡片

MOSS 不是单个 checkpoint 替换就能完成，需要完整的 MOSS/PornMaster 模型栈：

- UNET
- 文本编码器
- VAE
- 匹配的工作流

先让 DSH 盘点 `model_files.moss` 的三个文件是否都存在，再决定是否下载。不要只下载一个 checkpoint 就宣称接入完成。

如果有多个 MOSS 变体，先测试 1 张 832×1216，并报告实际加载的 UNET、文本编码器和 VAE 文件名。

## 可选：Krea2 / Qwen / Anima

这三个同样不是“换一个 checkpoint”：

- Krea2：UNET + CLIP + VAE
- Qwen：UNET + CLIP + VAE
- Anima：UNET + CLIP + VAE

简洁底模卡片只负责切换目标和工作流，不会伪造缺失的模型文件。下载后要更新 `config.json` 的 `model_files`，或者让 DSH 先盘点再配置。

