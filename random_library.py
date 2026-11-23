# -*- coding: utf-8 -*-
"""V5 random prompt library: SFW/NSFW sections, curated and template prompts."""

from __future__ import annotations

import copy
import json
import random
import re
from pathlib import Path

MODES = ("混合", "精选", "模板")
MIXED = "混合"
MAX_PROMPTS = 5000
MAX_CATEGORY_NAME = 32
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


class LibraryError(ValueError):
    pass


def default_library(categories, styles=None, templates=None,
                    nsfw_categories=None, nsfw_styles=None, nsfw_templates=None,
                    nsfw_weights=None):
    """Build a normalized library from the app's built-in constants."""
    styles = styles or {}
    out = {"version": 1, "categories": {}, "templates": {}}
    for name, prompts in categories.items():
        out["categories"][name] = {
            "style": styles.get(name, "写实"),
            "prompts": list(prompts),
        }
    for name, tpl in (templates or {}).items():
        out["templates"][name] = copy.deepcopy(tpl)
    if nsfw_categories:
        nsfw_styles = nsfw_styles or {}
        nsfw_weights = nsfw_weights or {}
        out["nsfw_categories"] = {}
        for name, prompts in nsfw_categories.items():
            out["nsfw_categories"][name] = {
                "style": nsfw_styles.get(name, "电影感"),
                "prompts": list(prompts),
                "weight": nsfw_weights.get(name, 1),
            }
        out["nsfw_templates"] = copy.deepcopy(nsfw_templates or {})
    return normalize(out)


def _normalize_section(categories, templates, start_total=0):
    if not isinstance(categories, dict) or not categories:
        raise LibraryError("分类必须是非空对象")
    if not isinstance(templates, dict):
        raise LibraryError("templates 必须是对象")
    out_categories = {}
    out_templates = {}
    total = start_total
    for raw_name, raw in categories.items():
        name = str(raw_name).strip()
        if not name or len(name) > MAX_CATEGORY_NAME:
            raise LibraryError("分类名不能为空且不超过 32 字符")
        if isinstance(raw, list):
            raw = {"prompts": raw}
        if not isinstance(raw, dict):
            raise LibraryError(f"分类“{name}”格式错误")
        prompts = []
        for item in raw.get("prompts", []):
            if not isinstance(item, str):
                continue
            item = item.strip()
            if item:
                prompts.append(item)
        if not prompts:
            raise LibraryError(f"分类“{name}”没有有效提示词")
        total += len(prompts)
        if total > MAX_PROMPTS:
            raise LibraryError(f"提示词总数超过 {MAX_PROMPTS}")
        try:
            weight = max(0.1, float(raw.get("weight", 1)))
        except (TypeError, ValueError):
            weight = 1.0
        out_categories[name] = {
            "style": str(raw.get("style") or "写实").strip() or "写实",
            "prompts": prompts,
            "weight": weight,
        }

    for raw_name, raw in templates.items():
        name = str(raw_name).strip()
        if name not in out_categories or not isinstance(raw, dict):
            continue
        fmt = str(raw.get("format") or "").strip()
        parts = raw.get("parts")
        if not fmt or not isinstance(parts, dict):
            continue
        clean_parts = {}
        for key, values in parts.items():
            if not isinstance(values, list):
                continue
            vals = [str(v).strip() for v in values if str(v).strip()]
            if vals:
                clean_parts[str(key)] = vals
        if not clean_parts:
            continue
        needed = set(PLACEHOLDER.findall(fmt))
        if not needed or not needed.issubset(clean_parts.keys()):
            continue
        out_templates[name] = {
            "style": str(raw.get("style") or out_categories[name]["style"]).strip(),
            "format": fmt,
            "parts": clean_parts,
        }
    return out_categories, out_templates, total


def normalize(data):
    if not isinstance(data, dict):
        raise LibraryError("随机库必须是 JSON 对象")
    categories, templates, total = _normalize_section(
        data.get("categories"), data.get("templates", {}))
    out = {"version": 1, "categories": categories, "templates": templates}
    if data.get("nsfw_categories"):
        nsfw_cats, nsfw_tpls, total = _normalize_section(
            data.get("nsfw_categories"), data.get("nsfw_templates", {}), total)
        out["nsfw_categories"] = nsfw_cats
        out["nsfw_templates"] = nsfw_tpls
    return out


def load_user(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise LibraryError(f"无法读取随机库：{e}")
    return normalize(data)


def save_user(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(normalize(data), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _section(data, sfw):
    if not sfw and data.get("nsfw_categories"):
        return data["nsfw_categories"], data.get("nsfw_templates", {}), "NSFW"
    return data["categories"], data.get("templates", {}), "SFW"


def _weighted_choice(items, rng):
    total = sum(float(cat.get("weight", 1)) for _, cat in items)
    if total <= 0:
        return rng.choice(items)
    point = rng.random() * total
    acc = 0.0
    for item in items:
        acc += float(item[1].get("weight", 1))
        if point <= acc:
            return item
    return items[-1]


def _template_text(template, rng):
    values = {key: rng.choice(vals) for key, vals in template["parts"].items()}
    try:
        return template["format"].format(**values)
    except Exception:
        return ""


def pick(data, category=MIXED, mode="混合", sfw=True, rng=None):
    rng = rng or random
    data = normalize(data) if "version" not in data else data
    cats, templates, section = _section(data, sfw)
    if not cats and not sfw:
        cats, templates, section = data["categories"], data.get("templates", {}), "SFW"
    if category in cats:
        choices = [(category, cats[category])]
    elif category != MIXED:
        # SFW 绝不能回退到 NSFW；NSFW 缺分类才回退 SFW
        other = data.get("nsfw_categories", {}) if cats is data["categories"] else data["categories"]
        if not sfw and category in other:
            choices = [(category, other[category])]
            templates = data.get("templates", {}) if cats is data.get("nsfw_categories") else data.get("nsfw_templates", {})
            section = "SFW" if cats is data.get("nsfw_categories") else "NSFW"
        else:
            choices = list(cats.items())
    else:
        choices = list(cats.items())
    if not choices:
        raise LibraryError("没有可用分类")
    name, cat = _weighted_choice(choices, rng) if category == MIXED else choices[0]

    template = templates.get(name)
    use_template = template is not None and mode in ("模板", "混合")
    if mode == "混合" and template is not None:
        use_template = rng.random() < 0.5
    if use_template:
        text = _template_text(template, rng)
        if text:
            return {"text": text, "category": name, "section": section,
                    "style": template.get("style") or cat.get("style", "写实"),
                    "mode": "模板"}
    return {"text": rng.choice(cat["prompts"]), "category": name, "section": section,
            "style": cat.get("style", "写实"), "mode": "精选"}
