# -*- coding: utf-8 -*-
"""根据提示词自动选择 LoRA，并给强度；只从候选白名单选。"""

import json
import re
from pathlib import Path

import config as appconfig
import llm_client

CFG = appconfig.load_config()
_models = appconfig.model_options(CFG)
MODEL = CFG.get("llm_model") or (_models[0][1] if _models else "huihui_ai/qwen3.5-abliterated:9b")


def _tokens(text):
    return set(re.findall(r"[a-z0-9_.-]{3,}", str(text).lower()))


GENERIC_LORA_WORDS = {
    "style", "pose", "detail", "skin", "texture", "light", "lighting", "realism",
    "slider", "frame", "finger", "dark", "night", "cum", "creampie", "squirt",
    "breast", "breasts", "pussy", "nipple", "face", "hair", "eye", "eyes", "photo",
    "film", "cosplay", "clothing", "outfit", "makeup", "quality", "aesthetic",
    "expression", "mouth", "anatomy", "body", "thigh", "leg", "sharp", "background",
    "arm", "weight", "shot", "size", "tone", "flash", "resolution", "base", "mix",
    "moss", "krea", "krea2", "qwen", "illustrious", "noob", "sdxl", "anima",
    "pornmaster", "lora", "xl", "il", "v1", "v2", "v3", "v4", "v5", "v6", "v20",
}


def _is_character_lora(item, prompt_tokens, prompt_text=""):
    """文件名含非通用专名，且提示词没提到、又没有 style 等通用词时，视为角色 LoRA。"""
    stem = Path(str(item.get("name", ""))).stem.lower()
    words = set(re.findall(r"[a-z]{3,}|[\u4e00-\u9fff]{2,}", stem))
    prompt_words = set(prompt_tokens) | set(re.findall(r"[\u4e00-\u9fff]{2,}", prompt_text))
    distinctive = {w for w in words if w not in GENERIC_LORA_WORDS and w not in prompt_words}
    generic = {w for w in words if w in GENERIC_LORA_WORDS}
    return bool(distinctive) and not bool(generic & {"style", "pose", "effect", "expression", "clothing", "outfit"})


def rank_candidates(prompt, candidates, limit=24):
    p = _tokens(prompt)
    scored = []
    for item in candidates:
        if _is_character_lora(item, p, prompt):
            continue
        blob = " ".join(str(item.get(k, "")) for k in ("name", "label", "trigger", "base"))
        t = _tokens(blob)
        score = len(p & t)
        scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("name", "")).lower()))
    positive = [item for score, item in scored if score > 0]
    # 有明确相关项时，不把零命中的角色 LoRA 混进候选
    if len(positive) >= 3:
        return positive[:limit]
    return [item for _, item in scored[:limit]]


def auto_match(prompt, base, candidates, limit=24, model=None):
    if not prompt.strip():
        raise ValueError("提示词为空")
    if base == "Unknown":
        raise ValueError("底模未知，不能自动匹配")
    pool = [c for c in candidates if str(c.get("base", "")) == base]
    if not pool:
        raise ValueError(f"没有匹配 {base} 的候选 LoRA")
    pool = rank_candidates(prompt, pool, limit)
    lines = []
    for i, c in enumerate(pool, 1):
        trigger = c.get("trigger") or "无明确触发词"
        lines.append(f"{i}. {Path(str(c.get('path', c.get('name', '')))).name} | {trigger}")
    system = f"""你是本地 ComfyUI 的 LoRA 调度器。根据用户提示词，从候选 LoRA 中选择 1-3 个最合适的，并给 0.3-0.9 的强度。
只允许从候选里选，不要编造文件。
不要选择角色专属 LoRA，除非用户提示词明确提到该角色名；优先风格、效果、姿势、滑块、服装类。
目标底模：{base}

候选：
{chr(10).join(lines)}

只输出 JSON，不要解释：
{{"loras":[{{"file":"候选文件名","strength":0.65,"reason":"简短原因"}}]}}
硬限制：仅限 18+ 成年虚构角色；禁止未成年/幼态/真实人物性化。"""
    raw = llm_client.chat(
        CFG,
        payload["messages"],
        model=model or MODEL,
        temperature=0.3, num_ctx=16384, num_predict=800,
    )
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("LLM 没有返回 JSON")
    plan = json.loads(m.group(0))
    by_name = {Path(str(c.get("path", c.get("name", "")))).name.casefold(): c for c in pool}
    chosen = []
    for item in (plan.get("loras") or [])[:3]:
        fname = Path(str(item.get("file", "")).replace("\\", "/")).name.casefold()
        c = by_name.get(fname)
        if not c:
            continue
        try:
            strength = max(0.2, min(1.0, float(item.get("strength", 0.7))))
        except Exception:
            strength = 0.7
        chosen.append({
            "name": c["name"], "label": c.get("label", c["name"]),
            "path": c["path"], "base": c.get("base", base),
            "trigger": c.get("trigger", ""), "strength": round(strength, 2),
            "enabled": True, "reason": str(item.get("reason", ""))[:120],
        })
    if not chosen:
        raise ValueError("LLM 没有选中候选中的 LoRA")
    return chosen, raw
