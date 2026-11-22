# -*- coding: utf-8 -*-
"""Model capability guidance for the release build."""

NSFW_HINTS = {
    "MOSS Image（自然语言）": ("NSFW 可用", "MOSS/PornMaster 路线，成人向能力强；仍需 18+ 硬限制。"),
    "MOSS Image（PornMaster Skill）": ("NSFW 可用", "MOSS + PornMaster Skill，推荐成人向使用。"),
    "MOSS 布局 / 分镜": ("NSFW 可用", "布局/分镜能力与底模相同；注意多人年龄边界。"),
    "Anima（Danbooru tag）": ("NSFW 需 LoRA/测试", "Anima 偏二次元审美，成人向通常需要适配 LoRA。"),
    "Qwen-Image 2.1（自然语言）": ("SFW 优先", "Qwen 2.1 更偏通用/写实，NSFW 不作为默认能力。"),
    "H3（视频结构化）": ("视频模型", "H3 是视频提示词路线，不属于图片 NSFW 开关范围。"),
    "Illustrious / SDXL（tag）": ("NSFW 可用/需 LoRA", "WAI/Illustrious 可成人向；具体解剖与风格建议配 LoRA。"),
    "Krea 2（自然语言）": ("SFW 优先/需测试", "Krea2 偏摄影美学，成人向效果不保证。"),
}

LLM_GUIDE = [
    ("Ollama · Qwen3.5 9B Abliterated", "NSFW 可用", "本地、速度快；复杂构图和长提示词能力有限。"),
    ("Ollama · Qwen3.8 27B Abliterated", "NSFW 可用", "本地、质量更好；显存和速度压力更大。"),
    ("OpenAI 兼容 · 本地无审查模型", "取决于模型", "LM Studio/vLLM/llama.cpp 等是否允许成人内容由所加载模型决定。"),
    ("Strata / 自定义本地网关", "取决于底层模型", "如果暴露 OpenAI 兼容接口可以接入；NSFW 能力看模型与模板。"),
    ("OpenAI / Anthropic / Gemini 等云端", "通常 SFW only", "多数云端模型会拒绝成人向请求；不要把它当作 NSFW 模型。"),
    ("OpenRouter 等聚合服务", "取决于供应商", "同一模型在不同 provider 的政策可能不同，使用前看条款。"),
]

IMAGE_GUIDE = [
    ("MOSS / PornMaster", "MOSS", "NSFW 可用", "成人向首选；仍限 18+ 虚构角色。"),
    ("Illustrious / WAI", "Illustrious/SDXL", "NSFW 可用/需 LoRA", "二次元稳定；解剖和风格用 LoRA 提升。"),
    ("Pony", "Pony", "NSFW 可用/需 LoRA", "常见成人向生态；必须使用成年角色。"),
    ("SD1.5 anime checkpoint", "SD1.5", "NSFW 可用/需 LoRA", "老生态，模型和 LoRA 质量差异大。"),
    ("Krea2", "Krea2", "SFW 优先/需测试", "摄影感强，成人向不是主路线。"),
    ("Qwen-Image 2.1", "Qwen", "SFW 优先", "通用/写实强，成人向不保证。"),
    ("Anima", "Anima", "NSFW 需 LoRA/测试", "二次元模型，成人向需额外适配。"),
]


def hint_for_target(target):
    return NSFW_HINTS.get(str(target), ("未标注", "请先测试该模型，并遵守 18+ 硬限制。"))


def guide_text():
    lines = [
        "模型指南（建议，不是保证）",
        "",
        "硬限制：仅 18+ 虚构角色；禁止未成年/幼态/年龄不明；禁止真实人物性化。",
        "",
        "【LLM：负责写提示词】",
    ]
    for name, status, note in LLM_GUIDE:
        lines.append(f"- {name}｜{status}｜{note}")
    lines += ["", "【画图底模：负责实际出图】"]
    for name, base, status, note in IMAGE_GUIDE:
        lines.append(f"- {name}（{base}）｜{status}｜{note}")
    lines += [
        "",
        "重要：工作台的 NSFW 开关只影响 LLM 写提示词，不会解锁画图模型。",
        "画图能否成人向，取决于底模、LoRA、工作流和显存，不是开关本身。",
        "公开仓库、README、Issue 中不要上传露骨素材。",
    ]
    return "\n".join(lines)
