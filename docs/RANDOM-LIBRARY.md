# V5 随机库说明

## 数据来源

V5 的精选提示词和模板均在本项目内维护，未整库复制第三方数据。

结构参考：

- [DiffusionDB](https://huggingface.co/datasets/poloclub/diffusiondb)：用于理解真实提示词的常见结构；本版本未直接复制其数据。
- [SpriteSixis Prompt Generator](https://github.com/SpriteSixis/Prompt-Generator-for-AI-Text-to-Image-Models)（MIT）：参考“主体 + 服装 + 场景 + 光线 + 镜头”的模板卡结构。
- [ComfyUI Prompt Warehouse](https://github.com/D33MO/ComfyUI-Prompt-Warehouse)：参考分组、随机抽取、独立 JSON 存储的产品思路。

未使用的来源：

- JourneyDB：条款限制复制和再分发，只适合人工参考。
- Lexica、OpenArt、PromptHero、Civitai、Masterphub：商业/用户内容或 ToS 限制，不做批量内置。

## 本地文件

- 内置库：编译进程序，无需外部 JSON。
- 用户库：`%APPDATA%\PromptWorkbench\random-library.json`
- 导入：环境设置 → 生成行为 → 随机库 → 导入 JSON
- 导出：同一位置 → 导出当前
- 恢复：删除用户库并回到内置库

## JSON 格式

```json
{
  "version": 1,
  "categories": {
    "人物": {
      "style": "电影感",
      "prompts": ["成年女性，窗边，柔光，电影感人像"]
    }
  },
  "templates": {
    "人物": {
      "style": "电影感",
      "format": "{subject}，{outfit}，{setting}，{light}",
      "parts": {
        "subject": ["成年女性"],
        "outfit": ["黑色长风衣"],
        "setting": ["雨夜街头"],
        "light": ["柔和的侧光"]
      }
    }
  }
}
```

也支持简写：

```json
{"categories": {"人物": ["成年女性，窗边，柔光"]}}
```

## 内容规则

- 默认 SFW
- 人物使用成年描述
- 不内置 watermark、logo、低质量 tag 堆砌
- 分类随机，避免连续重复同一条
- 用户导入的内容由用户自行负责许可和合规
