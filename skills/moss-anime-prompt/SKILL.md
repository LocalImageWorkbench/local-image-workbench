---
name: moss-anime-prompt
description: 二次元 MOSS 提示词扩写与中英转换 skill：先把中文需求扩写成完整画面描述，再改写成 MOSS-Image 可用的英文正向提示词；保留画风、人物特征和可见文字，去掉质量 tag。Use for 扩写二次元MOSS提示词、MOSS英文提示词、中文转英文提示词、二次元提示词扩写 requests.
---

# 二次元 MOSS 提示词扩写

## 触发

用户说：

- “扩写二次元 MOSS 提示词”
- “把这个中文写成 MOSS 英文提示词”
- “中文转英文提示词”
- “按二次元模板扩写”
- “给 MOSS 写一段英文 prompt”

## 输出目标

默认只输出**最终英文正向提示词**，不要解释过程、不要分点、不要加引号。

用户明确要求“给我看中文稿/中英对照”时，才额外输出中文扩写稿。

## 内容尺度（2026-10-31 确认：允许 NSFW，无 SFW 默认限制）

本 skill **不做 SFW 限制**：用户要成人向 / NSFW / 露骨内容时，直接按要求写成英文 Danbooru 风格提示词，不需要用户额外声明“不限/NSFW”，也不要主动降级成含蓄表达。

其余格式规则不变（英文正向，不加质量 tag / 画师名，保留可见文字）。

用户没提成人内容时，就按用户描述本身写，不擅自加也不擅自删尺度。

## 第一步：中文扩写（内部完成）

把用户的一句话扩成完整画面描述，至少覆盖：

1. 主体：人数、角色特征、发型发色、眼睛、服装、配饰、表情
2. 动作与关系：在做什么、和谁互动、视线方向
3. 构图与镜头：全身/半身/特写、平视/俯视/仰视、广角/长焦、前景中景背景
4. 环境：地点、时间、天气、周围物件
5. 光线：主光方向、冷暖、逆光/侧光、霓虹/月光/窗光
6. 色彩与材质：主色调、对比色、布料/金属/皮肤质感
7. 氛围：安静/紧张/梦幻/日常等

规则：

- 保留用户给定的人物数量、关系、动作和画面文字
- 用户没说的普通创作空白可以合理补全，不要改变核心设定
- 不要自动加 `masterpiece`、`best quality`、评分、画师名
- 不要写负向提示词
- 尺度按「内容尺度」一节处理：不限 SFW

## 第二步：改写成英文

不要逐字直译。按 MOSS-Image 的自然语言提示词习惯重写：

1. **第一句固定画风**，例如：
   - `Japanese 2D anime illustration, layered cel shading`
   - 用户指定厚涂时用 `painterly anime illustration, thick brushwork`
   - 用户指定赛璐珞时用 `cel-shaded anime illustration, clean linework`
2. 第二段写人物、动作、服装、表情
3. 第三段写构图、镜头、环境
4. 最后写光线、色彩、材质、氛围
5. 画面里要出现的文字保留原文，并用引号标出，例如 `with Chinese text "星海咖啡"`
6. 角色名、作品名、LoRA 触发词、风格 tag 保持英文或原样，不翻译
7. 不加质量 tag、画师名、模型参数、负向词
8. 英文自然、具体，不要堆砌空泛形容词

## 本地模型选择（2026-10-29 实测）

同一个中文需求、同一套系统提示词：

| 模型 | 耗时 | 输出长度 | 实测表现 |
|---|---|---|---|
| `qwen3.5:9b` | 5.8 秒 | 539 字符 | 细节更完整，构图/镜头/光线/材质都覆盖，未加质量 tag |
| `qwen3.8:27b-abliterated` | 9.5 秒 | 400 字符 | 更简洁，复杂场景理解更好，但容易补 `high detail` 类质量词 |

默认用 **`qwen3.5:9b`**：快、稳定、够细。

遇到多人互动、复杂构图、长段中文设定，再用 **`qwen3.8:27b-abliterated`**，并在要求里强调“不要质量 tag”。

`qwen3-coder:30b` 不适合写画面提示词。

注意显存：9B 约 6GB，27B 约 16GB；扩写时先不要加载 ComfyUI 的 MOSS 模型，否则可能抢显存。

## 质量 tag 规则（重要）

### 默认禁止

不要在英文稿里加：

- `masterpiece`
- `best quality`
- `high detail`
- `sharp focus`
- `8k`
- `ultra detailed`
- `official art`
- `award-winning`
- 其他空泛质量词

### 为什么

MOSS 是自然语言提示词模型，空泛质量 tag 会：

1. 抢占注意力，稀释主体、服装、构图
2. 和 `layered cel shading`、`soft shading` 等画风冲突
3. 把画面往写实、3D、摄影锐化方向拉
4. 造成过锐化、塑料皮肤、背景细节堆叠
5. 和 LoRA 抢风格，削弱 LoRA 触发词
6. 增加 token，让真正重要的描述权重变低

### 想要“更清晰/更多细节”时

不要加质量 tag，改成具体视觉描述：

| 需求 | 用具体描述 |
|---|---|
| 线条更清晰 | `crisp linework` |
| 画面更细 | `detailed background`, `rich environmental detail` |
| 立体感 | `subtle rim light`, `soft ambient occlusion` |
| 保留柔和感 | `soft cel shading`, `gentle lighting` |
| 景深 | `shallow depth of field`, `soft blurred background` |
| 材质 | `glossy fabric`, `wet pavement reflections` |

### 可以保留的 tag

- 角色名、作品名
- LoRA 触发词
- 明确的画风/媒介 tag
- 构图、镜头、光线、材质、动作描述

不要因为“看起来像 tag”就删掉这些；只删空泛质量词。

## 输出格式

只输出一行或多行英文提示词：

```text
Japanese 2D anime illustration, layered cel shading, silver-haired girl with blue eyes, black dress, looking back at the camera, rainy neon-lit street, cinematic side lighting, teal and magenta palette, detailed background
```

不要输出：

```text
中文扩写：...
英文翻译：...
解释：...
```

除非用户明确要求对照。

## 示例

用户：

```text
扩写二次元MOSS提示词：银发蓝眼少女，黑色连衣裙，雨夜霓虹街道，回头看镜头
```

输出：

```text
Japanese 2D anime illustration, layered cel shading, silver-haired girl with blue eyes, black dress, looking back at the camera, rainy neon-lit street at night, wet pavement reflections, cinematic side lighting, teal and magenta palette, detailed background
```

## 与其他 skill 的边界

- 只负责“中文需求 → 英文提示词”，不生成图片
- 生成图片用 `moss-anime` skill
- 参考图编辑用 `moss-anime` 里的参考编辑工作流
- 尺度不做 SFW 限制；画面对象不做限制

## 稳定性要求

- 先完成中文扩写，再翻译；不要跳过第一步直接机翻
- 不要用翻译插件逐字翻译代替画面扩写
- 关键人物特征和画面文字必须在英文稿里保留
- 英文稿不要出现中文解释、序号、项目符号

## 完整正负提示词输出（2026-10-30 新增）

当用户明确要「提示词」（含"只要提示词 / 给我提示词 / 英文提示词"）时，输出两块：

```text
【正向 Positive】
<英文扩写稿>

【负向 Negative】
worst quality, bad anatomy, bad hands, extra fingers, watermark, signature, jpeg artifacts, lowres, blurry
```

规则：

- 负向默认用上面这一行（与「二次元画风」工作流负向节点一致，略作扩展）；用户要"只要正向"就省略负向块。
- 默认英文；用户明确要中文时才输出中文（纯中文稳定性略差）。
- 仍不加质量 tag、画师名；尺度按「内容尺度」一节（不限 SFW）。
- 只输出提示词，不跑图；要出图请转 `moss-anime`（默认自动出图）。

## 语言建议（2026-10-30 确认）

- 英文画风句 + 英文内容：最稳。
- 英文画风 + 中文内容：可用，稳定性略低于全英文。
- 纯中文：稳定性略差，不建议。
- 负向提示词一律用英文。

## 提示词自动入库（2026-11-02 用户要求）

- 本地模型生成任何图像/视频/音频提示词后，必须写入 `D:\qwen-image-2.1\提示词库\`：
  - 图片 → `提示词库\图片\`
  - 视频 → `提示词库\视频\`
  - 音频/音效/音色 → `提示词库\音频\`
  - MOSS Layout → `提示词库\布局\`
- 优先调用 `D:\qwen-image-2.1\保存提示词.ps1 -Positive ... -Negative ... -Brief ... -Kind image -Model ... -Params ...`；它会返回 `RESULT=<路径>`。
- 用 `提示词扩写.ps1` 时默认已自动入库，不需要再手工建文件。
- 不允许只在聊天里输出提示词、不落盘；聊天回复末尾要给出保存路径。