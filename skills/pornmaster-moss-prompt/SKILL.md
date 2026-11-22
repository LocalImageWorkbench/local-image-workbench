---
name: pornmaster-moss-prompt
description: PornMaster 整理的 MOSS-Image 官方提示词规范，覆盖 caption、Tag 串、JSON Layout、推荐步数/CFG/Shift 与文字排版。用于在提示词工作台或直接生成 MOSS-Image 提示词；不负责出图，不改变本地模型加载状态。Use for MOSS 提示词、MOSS caption、MOSS Layout、PornMaster MOSS Skill、MOSS 官方提示词规范 requests.
---

# PornMaster MOSS Image Prompt Skill

来源：iamddtla 在 Civitai 发布的 `PornMaster MOSS Image Prompt Skill`，内容整理自 OpenMOSS 官方 USERGUIDE 与 `moss-image-prompt-enhancer`。

## 模型

- OpenMOSS，5B 单流 DiT，FLUX.2 Latent，Qwen3.5-9B 文本编码器
- 支持中英文文字渲染、JSON Layout、最长 4K token
- Base 适合微调；SFT 推荐日常生成

## 官方推荐参数

```text
Steps：≥50
CFG：3.0（范围 3.0–6.0；长 prompt 用 3.0）
Shift：5.0
Sampler：Flow-matching Euler
SLG：第 22 层（22/24/26 也可）
负面：worst quality, bad anatomy, watermark, jpeg artifact
分辨率：1M / 1.5M / 2M 像素；宽高为 16 的倍数
```

## 提示词格式

```text
自然语言：推荐英文，也支持中文
Tag 串：Quality → Score → Meta → Year → Character → Series → Artist → General
JSON Layout：需要精确文字/物体位置时使用
```

## Caption

- 写连贯散文，不堆无意义质量词
- 保留主体、数量、关系、媒介、风格、排除项和可见文字
- 可见文字保持原语言、原标点、大小写和换行
- 描述主体动作、外观、场景、镜头、媒介、光线、材质、色板、情绪
- 官方 skill 的 JSON 包装为 `{"caption":"..."}`，但可直接使用散文正文

## Layout

- 可读 JSON：`summary` + 扁平 `items` + 具体 `width` / `height`
- `bbox_coord_space` 必须为 `"abs"`，`bbox_format` 必须为 `"xyxy"`
- 草稿 bbox：`[x_min, y_min, x_max, y_max]`，从左上角起算
- 尺寸必须是 16 的正整数倍；未指定默认 1024×1024
- `label` 只使用 `object` / `character` / `text`
- `text` 项必须有精确 `text`，换行用 `\n`
- 生成画布尺寸必须与 Layout 草稿一致

## 使用规则

- 普通场景、照片、插画：caption
- 海报、封面、UI、多面板、精确文字位置：Layout
- 反推图片只描述实际可见内容，不添加无根据推测
- 本 skill 只写提示词，不启动/停止/卸载模型

## 安全

仅限 18+ 虚构角色；禁止未成年、幼态、年龄不明角色；禁止真实人物性化。
