# -*- coding: utf-8 -*-
"""ComfyUI 工作流导入：标准 UI/API 工作流 → API 图，识别底模/LoRA/提示词节点。"""

import copy
import json
import re
from pathlib import Path

# 支持的核心节点及其 widget -> API 输入名
CORE_WIDGETS = {
    "CheckpointLoaderSimple": ["ckpt_name"],
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "VAELoader": ["vae_name"],
    "LoraLoaderModelOnly": ["lora_name", "strength_model"],
    "LoraLoader": ["lora_name", "strength_model", "strength_clip"],
    "ModelSamplingAuraFlow": ["shift"],
    "CLIPTextEncode": ["text"],
    "EmptyLatentImage": ["width", "height", "batch_size"],
    "EmptySD3LatentImage": ["width", "height", "batch_size"],
    "KSampler": ["seed", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "KSamplerAdvanced": ["add_noise", "noise_seed", "steps", "cfg", "sampler_name",
                          "scheduler", "start_at_step", "end_at_step", "return_with_leftover_noise"],
    "VAEDecode": [],
    "SaveImage": ["filename_prefix"],
    "PreviewImage": [],
}
# KSampler 的 widgets_values 里包含 control_after_generate，需要跳过的索引
WIDGET_INDEX = {
    "KSampler": [0, 2, 3, 4, 5, 6],
    "KSamplerAdvanced": [0, 1, 3, 4, 5, 6, 7, 8, 9],
}
SKIP_NODES = {"Note", "MarkdownNote"}
LINK_TYPES = {"MODEL", "CLIP", "VAE", "CONDITIONING", "LATENT", "IMAGE", "MASK"}
SAMPLERS = {"KSampler", "KSamplerAdvanced"}


class WorkflowImportError(Exception):
    pass


def _load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise WorkflowImportError(f"无法读取 JSON：{e}")
    if not isinstance(data, dict):
        raise WorkflowImportError("工作流不是 JSON 对象")
    return data


def _is_api(data):
    return bool(data) and all(isinstance(v, dict) and "class_type" in v for v in data.values())


def _infer_base(text):
    s = str(text).lower().replace("\\", "/")
    if "krea2" in s:
        return "Krea2"
    if "moss" in s:
        return "MOSS"
    if "qwen" in s or "qi2.1" in s or "qwen2.1" in s:
        return "Qwen"
    if "anima" in s:
        return "Anima"
    if "pony" in s:
        return "Pony"
    if "sd15" in s or "sd1.5" in s:
        return "SD15"
    if "illustrious" in s or "sdxl" in s or "noob" in s:
        return "Illustrious/SDXL"
    return "Unknown"


def _ui_to_api(data):
    if data.get("definitions", {}).get("subgraphs"):
        raise WorkflowImportError("工作流使用了子图（subgraph），暂不支持；请在 ComfyUI 里展开/导出标准节点")
    nodes = data.get("nodes")
    links = data.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise WorkflowImportError("不是 ComfyUI UI 工作流（缺 nodes/links）")
    by_id = {int(n["id"]): n for n in nodes}
    link_map = {int(l[0]): l for l in links}
    unsupported = []
    for n in nodes:
        t = n.get("type")
        if t in SKIP_NODES:
            continue
        if t not in CORE_WIDGETS:
            unsupported.append(t)
    if unsupported:
        raise WorkflowImportError("包含未支持节点：" + "、".join(sorted(set(unsupported))))
    api = {}
    for n in nodes:
        t = n.get("type")
        if t in SKIP_NODES:
            continue
        nid = str(n["id"])
        inputs = {}
        # 连线输入
        for inp in n.get("inputs", []):
            lid = inp.get("link")
            if lid is None:
                continue
            l = link_map.get(int(lid))
            if not l:
                continue
            src = str(l[1])
            inputs[inp["name"]] = [src, int(l[2])]
        # widget 输入
        vals = n.get("widgets_values") or []
        names = CORE_WIDGETS[t]
        idxs = WIDGET_INDEX.get(t, list(range(len(names))))
        for i, name in zip(idxs, names):
            if i < len(vals):
                inputs[name] = vals[i]
        api[nid] = {"class_type": t, "inputs": inputs}
    return api


def _source_of(api, sampler_id, slot_name):
    inputs = api.get(str(sampler_id), {}).get("inputs", {})
    ref = inputs.get(slot_name)
    if isinstance(ref, list) and ref:
        return str(ref[0])
    return None


def _find_prompts(api):
    positive = negative = None
    for nid, node in api.items():
        if node.get("class_type") in SAMPLERS:
            p = _source_of(api, nid, "positive")
            n = _source_of(api, nid, "negative")
            if p and api.get(p, {}).get("class_type") == "CLIPTextEncode":
                positive = p
            if n and api.get(n, {}).get("class_type") == "CLIPTextEncode":
                negative = n
    return positive, negative


def load_workflow(path):
    data = _load(path)
    is_api = _is_api(data)
    api = data if is_api else _ui_to_api(data)
    if not isinstance(api, dict) or not api:
        raise WorkflowImportError("工作流为空")
    positive, negative = _find_prompts(api)
    if not positive:
        raise WorkflowImportError("找不到 KSampler 连接的正向 CLIPTextEncode")
    base_text = []
    loras = []
    for node in api.values():
        t = node.get("class_type")
        inputs = node.get("inputs", {})
        if t == "CheckpointLoaderSimple":
            base_text.append(inputs.get("ckpt_name", ""))
        elif t == "UNETLoader":
            base_text.append(inputs.get("unet_name", ""))
        if t in ("LoraLoaderModelOnly", "LoraLoader"):
            name = inputs.get("lora_name")
            if name:
                loras.append(name)
    return {
        "path": str(path),
        "format": "API" if is_api else "UI",
        "api": api,
        "positive": positive,
        "negative": negative,
        "base": _infer_base(" ".join(map(str, base_text))),
        "loras": loras,
        "node_count": len(api),
    }


def prepare(imported, positive_text, negative_text, count=1):
    api = copy.deepcopy(imported["api"])
    if imported.get("positive") in api:
        api[imported["positive"]]["inputs"]["text"] = positive_text
    if imported.get("negative") in api:
        api[imported["negative"]]["inputs"]["text"] = negative_text
    count = max(1, min(8, int(count)))
    for node in api.values():
        if node.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage"):
            node["inputs"]["batch_size"] = count
    return api


LORA_TYPES = ("LoraLoaderModelOnly", "LoraLoader")
ZH_HINTS = {
    "自慰": "masturbation", "手指": "finger", "插入": "insert", "张开": "spread",
    "小穴": "pussy", "喷水": "squirt", "高潮": "orgasm", "胸": "breast",
    "口": "mouth", "玩具": "toy", "假阳具": "dildo", "肛": "anal",
    "裸": "nude", "衣服": "clothing",
}


def _words(text):
    text = str(text).lower()
    out = set(re.findall(r"[a-z]{3,}", text))
    for zh, en in ZH_HINTS.items():
        if zh in text:
            out.add(en)
    return out


def _lora_group(stem):
    if "facebreastpussy" in stem:
        return "core"
    if "sexymouth" in stem:
        return "mouth"
    if "clothing_" in stem or "intimatejewelry" in stem:
        return "clothing"
    if "butthole" in stem:
        return "anal"
    if "pussy_" in stem:
        return "pussy_variant"
    if any(x in stem for x in ("sextoy", "sex toy", "kinkytoys", "fleshlight", "dildo",
                               "condom", "lovedoll", "roaster", "pump", "balls")):
        return "toy"
    if "endofhistory" in stem:
        return "style"
    if any(x in stem for x in ("style", "aesthetic", "artist", "painting", "realism")):
        return "style"
    if "pose" in stem:
        return "pose"
    if any(x in stem for x in ("detail", "skin", "texture")):
        return "detail"
    return "other"


def _lora_score(group, stem, words):
    if group == "pussy_variant":
        if "spreading" in stem and words & {"spread", "spreading", "gaping", "open", "finger", "insert"}:
            return 4.0
        if "cameltoe" in stem and "cameltoe" in words:
            return 3.0
        if "butterfly" in stem and "butterfly" in words:
            return 3.0
        if "lily" in stem and "lily" in words:
            return 3.0
        if "peach" in stem and words & {"peach", "rear", "behind"}:
            return 3.0
        if "lotte" in stem and "lotte" in words:
            return 3.0
        return 0.0
    if group == "core":
        return 2.0 if words & {"pussy", "breast", "breasts", "face", "finger", "nude", "masturbation"} else 0.0
    if group == "toy":
        return 2.2 if words & {"toy", "toys", "dildo", "fleshlight", "condom", "pump", "machine"} else 0.0
    if group == "clothing":
        return 1.8 if words & {"clothing", "clothes", "jewelry", "pearls", "outfit", "dress"} else 0.0
    if group == "anal":
        return 2.0 if words & {"anal", "butt", "ass", "rear"} else 0.0
    if group == "mouth":
        return 1.2 if words & {"mouth", "oral", "kiss", "suck"} else 0.0
    if group == "style":
        return 0.6
    if group == "pose":
        return 0.5 if words & {"pose", "sitting", "standing", "lying", "kneeling"} else 0.2
    if group == "detail":
        return 0.4 if words & {"detail", "details", "skin", "texture"} else 0.0
    if group == "other":
        name_words = set(re.findall(r"[a-z]{3,}", stem))
        return min(1.5, 0.4 * len(words & name_words))
    return 0.0


def plan_loras(api, positive, negative=""):
    """同类互斥只留一个；不同功能组可叠加；总数和总强度封顶。"""
    nodes = []
    for nid, node in api.items():
        if node.get("class_type") not in LORA_TYPES:
            continue
        name = node.get("inputs", {}).get("lora_name", "")
        stem = Path(str(name).replace("\\", "/")).stem.lower()
        group = _lora_group(stem)
        score = _lora_score(group, stem, _words(positive))
        nodes.append({"node": str(nid), "name": name, "group": group,
                      "score": score, "class_type": node.get("class_type"),
                      "current_strength": float(node.get("inputs", {}).get("strength_model", 0.8))})
    if len(nodes) <= 3:
        return [{"node": x["node"], "name": x["name"], "group": x["group"],
                 "class_type": x["class_type"], "enabled": True,
                 "strength": round(x["current_strength"], 2),
                 "reason": "LoRA 数量少，保持原强度"} for x in nodes], \
               {"enabled": len(nodes), "bypassed": 0, "negative": 0}

    chosen = []
    # 每个功能组只选最高分的一个；不同组允许叠加
    for group in ("core", "pussy_variant", "toy", "clothing", "anal", "mouth",
                  "style", "pose", "detail", "other"):
        candidates = [x for x in nodes if x["group"] == group and x["score"] > 0]
        if not candidates:
            continue
        chosen.append(max(candidates, key=lambda x: x["score"]))
    if not chosen:
        chosen = [max(nodes, key=lambda x: x["score"])]
    # 最多 6 个不同功能组，优先匹配分数高的
    chosen.sort(key=lambda x: -x["score"])
    chosen = chosen[:6]
    chosen_ids = {x["node"] for x in chosen}
    plan = []
    for x in nodes:
        enabled = x["node"] in chosen_ids
        if enabled:
            strength = {"core": 0.4, "pussy_variant": 0.45, "toy": 0.4,
                        "clothing": 0.3, "anal": 0.35, "mouth": 0.25,
                        "style": 0.2, "pose": 0.25, "detail": 0.25,
                        "other": 0.25}.get(x["group"], 0.25)
            reason = "可叠加功能组"
        else:
            strength = 0.0
            reason = "同类互斥/无关，旁路"
        plan.append({"node": x["node"], "name": x["name"], "group": x["group"],
                     "class_type": x["class_type"], "enabled": enabled,
                     "strength": round(strength, 2), "reason": reason})
    # 总强度封顶 2.4，允许比 3 个更多的可叠加组
    total = sum(abs(x["strength"]) for x in plan if x["enabled"])
    if total > 2.4:
        scale = 2.4 / total
        for x in plan:
            if x["enabled"]:
                x["strength"] = round(x["strength"] * scale, 2)
    enabled = sum(1 for x in plan if x["enabled"])
    return plan, {"enabled": enabled, "bypassed": len(plan) - enabled, "negative": 0}


def apply_lora_plan(api, plan):
    out = copy.deepcopy(api)
    by_id = {x["node"]: x for x in plan}
    disabled = {x["node"] for x in plan if not x["enabled"]}
    for x in plan:
        nid = x["node"]
        if nid not in out:
            continue
        node = out[nid]
        if x["enabled"]:
            if "strength_model" in node.get("inputs", {}):
                node["inputs"]["strength_model"] = float(x["strength"])
        elif node.get("class_type") == "LoraLoaderModelOnly":
            continue
        else:
            # LoraLoader 的 CLIP 输出可能被引用，不能直接摘节点
            node["inputs"]["strength_model"] = 0.0
            if "strength_clip" in node.get("inputs", {}):
                node["inputs"]["strength_clip"] = 0.0

    def resolve(ref):
        seen = set()
        while str(ref[0]) in disabled:
            nid = str(ref[0])
            if nid in seen:
                break
            seen.add(nid)
            node = out.get(nid, {})
            src = node.get("inputs", {}).get("model")
            if not src:
                break
            ref = src
        return ref

    for node in out.values():
        for key, value in list(node.get("inputs", {}).items()):
            if isinstance(value, list) and len(value) == 2 and str(value[0]) in disabled:
                node["inputs"][key] = resolve(value)
    for nid in disabled:
        if out.get(nid, {}).get("class_type") == "LoraLoaderModelOnly":
            out.pop(nid, None)
    return out
